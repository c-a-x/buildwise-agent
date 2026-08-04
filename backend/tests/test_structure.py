from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_spec_required_runtime_files_and_demo_images_exist():
    required_files = (
        PROJECT_ROOT / "frontend/src/router/guards.ts",
        PROJECT_ROOT / "backend/app/api/v1/endpoints/modules.py",
        PROJECT_ROOT / "data_demo/images/safety_no_helmet.jpg",
        PROJECT_ROOT / "data_demo/images/safety_normal.jpg",
    )

    for path in required_files:
        assert path.is_file(), f"规格要求的文件不存在: {path}"

    for image_path in required_files[-2:]:
        content = image_path.read_bytes()
        assert content.startswith(b"\xff\xd8"), f"不是 JPEG 文件: {image_path}"
        assert content.endswith(b"\xff\xd9"), f"JPEG 文件未正常结束: {image_path}"


def test_module_routes_are_separated_from_health_endpoint():
    health_source = (
        PROJECT_ROOT / "backend/app/api/v1/endpoints/health.py"
    ).read_text(encoding="utf-8")
    assert 'router.get("/modules")' not in health_source

