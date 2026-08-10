import importlib.util
from pathlib import Path

from app.core.config import Settings


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_providers.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_providers", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provider_precheck_is_read_only_and_returns_actionable_output(capsys):
    module = load_script_module()
    capabilities = module.collect_capabilities(Settings())

    assert len(capabilities) == 7
    output = module.render_report(capabilities)
    assert "视觉识别" in output
    assert "模拟" in output
    assert "下一步" in output
    assert "数据库" not in output
    assert not capsys.readouterr().out


def test_provider_precheck_exit_code_is_zero_for_default_offline_configuration(capsys):
    module = load_script_module()

    exit_code = module.run(Settings())

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Provider 预检" in output
    assert "WARNING" in output or "SIMULATED" in output


def test_provider_precheck_labels_configured_status():
    module = load_script_module()

    assert module._status_label("configured") == "CONFIGURED"
