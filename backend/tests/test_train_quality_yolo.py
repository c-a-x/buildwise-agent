"""Regression tests for the standalone quality-model training utility."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "train_quality_yolo.py"
SPEC = importlib.util.spec_from_file_location("train_quality_yolo", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
training_script = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = training_script
SPEC.loader.exec_module(training_script)


def test_parse_label_clips_only_the_staged_copy(tmp_path: Path) -> None:
    label_path = tmp_path / "edge.txt"
    label_path.write_text("0 0.05 0.5 0.2 0.4\n", encoding="utf-8")

    counts, normalized_label, repaired_boxes = training_script.parse_label(label_path)

    assert counts == {0: 1}
    assert repaired_boxes == 1
    assert normalized_label == "0 0.075 0.5 0.15 0.4\n"
    assert label_path.read_text(encoding="utf-8") == "0 0.05 0.5 0.2 0.4\n"


def test_data_yaml_references_final_dataset_directory(tmp_path: Path) -> None:
    final_data_dir = tmp_path / "quality_yolo"
    config = training_script.TrainingConfig(
        dataset_dir=tmp_path / "source",
        data_dir=final_data_dir,
        base_model=tmp_path / "base.pt",
        model_output=tmp_path / "best.pt",
        samples_dir=tmp_path / "samples",
        runs_dir=tmp_path / "runs",
        run_name="quality_mbdd",
        seed=7,
        val_ratio=0.1,
        epochs=1,
        image_size=640,
        batch=1,
        workers=0,
        device="cpu",
        nms_fallback="off",
        validation_interval=10,
        verbose=False,
        progress_width=24,
    )
    staged_yaml = tmp_path / "staging" / "data.yaml"
    staged_yaml.parent.mkdir()

    training_script.write_data_yaml(config, staged_yaml)

    assert f"path: {final_data_dir.resolve().as_posix()}" in staged_yaml.read_text(encoding="utf-8")


def test_validation_epochs_always_includes_the_final_epoch() -> None:
    assert training_script.validation_epochs(50, 10) == (10, 20, 30, 40, 50)
    assert training_script.validation_epochs(25, 10) == (10, 20, 25)


def test_training_is_the_default_and_reuse_is_opt_in() -> None:
    parser = training_script.build_parser()

    assert parser.parse_args([]).reuse_train is False
    assert parser.parse_args([]).batch == 48
    assert parser.parse_args([]).progress_width == 24
    assert parser.parse_args([]).verbose is False
    assert parser.parse_args(["--reuse-train"]).reuse_train is True
