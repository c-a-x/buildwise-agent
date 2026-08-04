"""LLM 隐患分析层（源自 safety-scout）。

把 safety-scout 的多模态 LLM 分析能力适配为 buildwise 的**同步**调用链：
- claude_cli：子进程 `claude -p` + Read 工具读图 + --json-schema 约束输出
- doubao：httpx.Client 调火山方舟 OpenAI 兼容接口，图片 base64 data URI

调用链全程同步（subprocess / httpx.Client），禁用 asyncio，避免与
FastAPI async endpoint 的同步 provider 路径冲突。任何异常只降级不抛出。
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.providers.vision.mapping import llm_finding_to_hazard

SYSTEM_PROMPT = (
    "你是一名资深建筑工地安全员，负责对施工现场照片进行安全隐患排查。"
    "你的分析必须严谨、专业、基于图片中实际可见的内容，不得凭空编造隐患或规范条款。"
)

ANALYZE_PROMPT = """请分析这张施工现场照片，识别其中的安全隐患。

隐患分类（category_code）：
H1 高处坠落 | H2 物体打击 | H3 触电 | H4 坍塌 | H5 机械伤害
H6 火灾 | H7 中毒窒息 | H8 起重伤害 | H9 个人防护缺失 | H10 其他/文明施工

要求：
1. 逐条列出所有可确认的隐患，每条的 category_code/category_name 对应上述分类；
2. description 用中文简洁描述隐患位置和状态（1 句）；
3. severity 取 high/medium/low 三档，按可能导致事故的后果严重度判断；
4. regulation 引用真实、适用的规范条款，格式为《规范名称》第X.Y.Z条；
   不确定或无法确认的引用不要编造，填空字符串；
5. suggestion 给出具体、可执行的整改建议（1 句）；
6. confidence 为 0~1 的判断置信度；
7. 若符合重大事故隐患情形（参考建质规〔2024〕5号），is_major 置 true 并
   在 major_basis 中说明判定依据；
8. 如果图片中确认没有隐患，返回 {"hazards": []}，不要强行编造。

只输出 JSON，不要输出任何解释文字。JSON 结构：
{"hazards": [{"category_code": "H1", "category_name": "高处坠落", "description": "...", "severity": "high", "regulation": "《...》第X.Y.Z条", "suggestion": "...", "confidence": 0.9, "is_major": false, "major_basis": ""}]}
"""

_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hazards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category_code": {"type": "string", "enum": ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10"]},
                    "category_name": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "regulation": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "is_major": {"type": "boolean"},
                    "major_basis": {"type": "string"},
                },
                "required": ["category_code", "category_name", "description", "severity"],
            },
        }
    },
    "required": ["hazards"],
}


def _parse_findings(raw_text: str) -> list[dict[str, Any]] | None:
    """解析 LLM 输出的 JSON，校验 hazards 结构。失败返回 None。"""
    text = (raw_text or "").strip()
    if not text:
        return None
    # 兼容包裹在 markdown 代码块或首尾杂文本中的 JSON
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    hazards = payload.get("hazards") if isinstance(payload, dict) else None
    if not isinstance(hazards, list):
        return None
    findings: list[dict[str, Any]] = []
    for item in hazards:
        if not isinstance(item, dict) or not str(item.get("category_code", "")).strip().startswith("H"):
            continue
        findings.append(item)
    return findings or None


def _mime_type(image_path: str) -> str:
    suffix = Path(image_path).suffix.lower()
    return {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suffix, "image/jpeg")


def _find_git_bash() -> str | None:
    """定位 git-bash 的 bash.exe，供 claude CLI 在 Windows 下启动子进程。"""
    env_path = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    git_exe = shutil.which("git")
    if git_exe:
        git_dir = Path(git_exe).resolve().parent
        for parent in (git_dir, *git_dir.parents):
            candidate = parent / "usr" / "bin" / "bash.exe"
            if candidate.exists():
                return str(candidate)
    for fixed in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if Path(fixed).exists():
            return fixed
    return None


class LLMHazardAnalyzer:
    """同步多模态 LLM 隐患分析器。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.vision_llm_provider
        self.timeout = settings.vision_llm_timeout

    def analyze_sync(self, image_path: str) -> tuple[list[dict[str, Any]], bool]:
        """返回 (buildwise hazard 列表, 是否成功执行)。

        ok=True 表示 LLM 引擎配置且调用成功（hazards 可能为空 = 确认无隐患）；
        ok=False 表示未配置或调用失败（需降级）。
        """
        if self.provider == "claude_cli":
            ok, findings = self._claude_cli(image_path)
        elif self.provider == "doubao":
            ok, findings = self._doubao(image_path)
        else:
            return [], False
        if not ok:
            return [], False
        return [llm_finding_to_hazard(finding) for finding in findings], True

    def _claude_cli(self, image_path: str) -> tuple[bool, list[dict[str, Any]]]:
        cmd = shutil.which(self.settings.vision_llm_claude_cmd) or self.settings.vision_llm_claude_cmd
        # 图片作为「原生附件」以位置参数 + 绝对路径传入。
        # 实测 Read 工具在 Windows 读图极不稳定(>90s 超时)，原生附件 ~48s 成功。
        image_abs = str(Path(image_path).resolve())
        args = [
            cmd,
            "-p",
            ANALYZE_PROMPT,
            "--system-prompt",
            SYSTEM_PROMPT,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--json-schema",
            json.dumps(_JSON_SCHEMA, ensure_ascii=False),
            image_abs,
        ]
        env = dict(os.environ)
        bash_path = _find_git_bash()
        if bash_path:
            env["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except (FileNotFoundError, OSError):
            return False, []
        try:
            # 注意：不用 text=True（Windows GBK 会崩），原始字节 + 手动 decode
            stdout, _stderr = proc.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            # Windows 下 subprocess.run(timeout) 不杀进程树，node.exe 残留占管道
            # 手动 taskkill /T /F 整棵子树，再回收，避免永久阻塞
            self._kill_tree(proc)
            return False, []
        if proc.returncode != 0:
            return False, []
        try:
            stdout = stdout.decode("utf-8", errors="replace")
            envelope = json.loads(stdout.strip() or "{}")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            envelope = {}
        if isinstance(envelope, dict) and envelope.get("is_error"):
            return False, []
        raw = None
        if isinstance(envelope, dict):
            structured = envelope.get("structured_output")
            raw = json.dumps(structured, ensure_ascii=False) if structured else envelope.get("result")
        if not raw:
            return False, []
        findings = _parse_findings(str(raw))
        return True, (findings or [])

    @staticmethod
    def _kill_tree(proc: subprocess.Popen) -> None:
        """Windows 下杀死进程及其整棵子树（含 node.exe 子进程）。"""
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            except (subprocess.SubprocessError, OSError):
                pass
        try:
            proc.kill()
        except OSError:
            pass

    def _doubao(self, image_path: str) -> tuple[bool, list[dict[str, Any]]]:
        settings = self.settings
        base_url = (settings.llm_base_url or "").rstrip("/")
        api_key = settings.llm_api_key
        model = settings.llm_model
        if not base_url or not api_key or not model:
            return False, []
        try:
            with open(image_path, "rb") as handle:
                image_b64 = base64.b64encode(handle.read()).decode("ascii")
        except OSError:
            return False, []
        data_uri = f"data:{_mime_type(image_path)};base64,{image_b64}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": ANALYZE_PROMPT},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError, OSError):
            return False, []
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return False, []
        findings = _parse_findings(str(content))
        return True, (findings or [])
