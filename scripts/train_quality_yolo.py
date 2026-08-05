"""Prepare an MBDD-style YOLO dataset and train a quality inspection model.

The script is deliberately independent from the FastAPI application.  It only
creates training artefacts; publishing the resulting model is an explicit copy
step performed after a successful training run.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import shutil
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:
    from torch import Tensor

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = PROJECT_DIR / "MBDD2025"
DEFAULT_DATA_DIR = PROJECT_DIR / "data_demo" / "quality_yolo"
DEFAULT_BASE_MODEL = PROJECT_DIR / "backend" / "storage" / "models" / "yolov8n.pt"
DEFAULT_MODEL_OUTPUT = PROJECT_DIR / "backend" / "storage" / "models" / "yolov8n-5cls-mbdd.pt"
DEFAULT_SAMPLES_DIR = PROJECT_DIR / "frontend" / "src" / "assets" / "samples"
DEFAULT_RUNS_DIR = PROJECT_DIR / "runs" / "detect"

DEFECT_NAMES = ("crack", "leakage", "abscission", "corrosion", "bulge")
SAMPLE_CLASSES = ("crack", "leakage", "abscission")
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})
COORDINATE_TOLERANCE = 1e-6


@dataclass(frozen=True)
class TrainingConfig:
    dataset_dir: Path
    data_dir: Path
    base_model: Path
    model_output: Path
    samples_dir: Path
    runs_dir: Path
    run_name: str
    seed: int
    val_ratio: float
    epochs: int
    image_size: int
    batch: int
    workers: int
    device: str
    nms_fallback: str
    validation_interval: int
    verbose: bool
    progress_width: int

    @property
    def images_dir(self) -> Path:
        return self.dataset_dir / "JPEGImages"

    @property
    def labels_dir(self) -> Path:
        return self.dataset_dir / "Labels"

    @property
    def data_yaml(self) -> Path:
        return self.data_dir / "data.yaml"

    @property
    def run_dir(self) -> Path:
        return self.runs_dir / self.run_name


@dataclass(frozen=True)
class ImageRecord:
    image_path: Path
    label_path: Path | None
    normalized_label: str | None = None

    @property
    def stem(self) -> str:
        return self.image_path.stem


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def ratio(value: str) -> float:
    parsed = float(value)
    if not 0 < parsed < 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return parsed


def link_or_copy(source: Path, destination: Path) -> None:
    """Create a same-volume hard link, falling back to a metadata-preserving copy."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def with_progress(items: Iterable[object], total: int, description: str) -> Iterable[object]:
    """Show a terminal progress bar when tqdm is available."""
    try:
        from tqdm import tqdm
    except ImportError:
        return items
    return tqdm(items, total=total, desc=description, unit="image", dynamic_ncols=True)


def validate_image(image_path: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to validate training images. Install it with: pip install Pillow") from exc

    try:
        with Image.open(image_path) as image:
            image.verify()
    except (OSError, ValueError, SyntaxError) as exc:
        raise ValueError(f"Unreadable image: {image_path}") from exc


def parse_label(label_path: Path) -> tuple[Counter[int], str | None, int]:
    """Validate a YOLO label and clip only boxes that exceed image boundaries."""
    try:
        content = label_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Label is not UTF-8 text: {label_path}") from exc

    class_counts: Counter[int] = Counter()
    normalized_lines: list[str] = []
    repaired_boxes = 0
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        values = line.split()
        if len(values) != 5:
            raise ValueError(f"{label_path}:{line_number} must contain 5 values, got {len(values)}")
        try:
            class_id = int(values[0])
            x_center, y_center, width, height = (float(value) for value in values[1:])
        except ValueError as exc:
            raise ValueError(f"{label_path}:{line_number} contains a non-numeric value") from exc
        if not 0 <= class_id < len(DEFECT_NAMES):
            raise ValueError(f"{label_path}:{line_number} has unsupported class id {class_id}")
        coordinates = (x_center, y_center, width, height)
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError(f"{label_path}:{line_number} contains a non-finite coordinate")
        if not 0 <= x_center <= 1 or not 0 <= y_center <= 1 or not 0 < width <= 1 or not 0 < height <= 1:
            raise ValueError(f"{label_path}:{line_number} has coordinates outside YOLO's normalized range")
        left, top = x_center - width / 2, y_center - height / 2
        right, bottom = x_center + width / 2, y_center + height / 2
        clipped_left, clipped_top = max(0.0, left), max(0.0, top)
        clipped_right, clipped_bottom = min(1.0, right), min(1.0, bottom)
        if clipped_right - clipped_left <= COORDINATE_TOLERANCE or clipped_bottom - clipped_top <= COORDINATE_TOLERANCE:
            raise ValueError(f"{label_path}:{line_number} has no visible area after boundary clipping")
        if (clipped_left, clipped_top, clipped_right, clipped_bottom) != (left, top, right, bottom):
            repaired_boxes += 1
            x_center = (clipped_left + clipped_right) / 2
            y_center = (clipped_top + clipped_bottom) / 2
            width = clipped_right - clipped_left
            height = clipped_bottom - clipped_top
            normalized_lines.append(f"{class_id} {x_center:.12g} {y_center:.12g} {width:.12g} {height:.12g}")
        else:
            normalized_lines.append(line.strip())
        class_counts[class_id] += 1
    return class_counts, "\n".join(normalized_lines) + ("\n" if normalized_lines else ""), repaired_boxes


def find_records(config: TrainingConfig) -> tuple[list[ImageRecord], Counter[int], int, int]:
    if not config.images_dir.is_dir():
        raise FileNotFoundError(f"Image directory does not exist: {config.images_dir}")
    if not config.labels_dir.is_dir():
        raise FileNotFoundError(f"Label directory does not exist: {config.labels_dir}")

    image_paths = sorted(
        (path for path in config.images_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
        key=lambda path: (path.stem.casefold(), path.suffix.casefold()),
    )
    if not image_paths:
        raise FileNotFoundError(f"No supported images found in: {config.images_dir}")

    records: list[ImageRecord] = []
    class_counts: Counter[int] = Counter()
    missing_labels = 0
    repaired_boxes = 0
    seen_stems: set[str] = set()
    for image_path in with_progress(image_paths, len(image_paths), "Validating images"):
        assert isinstance(image_path, Path)
        normalized_stem = image_path.stem.casefold()
        if normalized_stem in seen_stems:
            raise ValueError(f"Multiple images share the same stem: {image_path.stem}")
        seen_stems.add(normalized_stem)
        validate_image(image_path)
        label_path = config.labels_dir / f"{image_path.stem}.txt"
        if label_path.exists():
            label_counts, normalized_label, label_repairs = parse_label(label_path)
            class_counts.update(label_counts)
            repaired_boxes += label_repairs
            records.append(
                ImageRecord(
                    image_path=image_path,
                    label_path=label_path,
                    normalized_label=normalized_label if label_repairs else None,
                )
            )
        else:
            # Ultralytics treats an image without a label file as a background image.
            missing_labels += 1
            records.append(ImageRecord(image_path=image_path, label_path=None))

    if len(records) < 2:
        raise ValueError("At least two valid images are required to create train and validation splits")
    return records, class_counts, missing_labels, repaired_boxes


def split_records(records: Sequence[ImageRecord], seed: int, val_ratio: float) -> tuple[list[ImageRecord], list[ImageRecord]]:
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)
    validation_count = min(len(shuffled) - 1, max(1, round(len(shuffled) * val_ratio)))
    return shuffled[validation_count:], shuffled[:validation_count]


def write_data_yaml(config: TrainingConfig, destination: Path) -> None:
    names = ", ".join(f'"{name}"' for name in DEFECT_NAMES)
    destination.write_text(
        "\n".join(
            (
                f"path: {config.data_dir.resolve().as_posix()}",
                "train: images/train",
                "val: images/val",
                f"nc: {len(DEFECT_NAMES)}",
                f"names: [{names}]",
                "",
            )
        ),
        encoding="utf-8",
    )


def replace_directory(staging_dir: Path, destination: Path) -> None:
    """Publish a fully built dataset directory, retaining the old directory on failure."""
    backup_dir = destination.with_name(f"{destination.name}.previous")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if destination.exists():
        destination.replace(backup_dir)
    try:
        staging_dir.replace(destination)
    except Exception:
        if backup_dir.exists() and not destination.exists():
            backup_dir.replace(destination)
        raise
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


def dataset_is_ready(config: TrainingConfig) -> bool:
    required_paths = (
        config.data_yaml,
        config.data_dir / "images" / "train",
        config.data_dir / "images" / "val",
        config.data_dir / "labels" / "train",
        config.data_dir / "labels" / "val",
        config.data_dir / "manifest.json",
    )
    return all(path.exists() for path in required_paths)


def legacy_dataset_is_usable(config: TrainingConfig) -> bool:
    required_paths = (
        config.data_yaml,
        config.data_dir / "images" / "train",
        config.data_dir / "images" / "val",
        config.data_dir / "labels" / "train",
        config.data_dir / "labels" / "val",
    )
    return all(path.exists() for path in required_paths)


def prepare_dataset(config: TrainingConfig, rebuild: bool) -> None:
    if dataset_is_ready(config) and not rebuild:
        print(f"[dataset] Reusing validated dataset: {config.data_dir}")
        return
    if legacy_dataset_is_usable(config) and not rebuild:
        print(f"[dataset] Reusing legacy dataset without a manifest: {config.data_dir}. Use --rebuild to validate and regenerate it.")
        return
    if config.data_dir.exists() and not rebuild:
        raise RuntimeError(f"Dataset directory is incomplete: {config.data_dir}. Run again with --rebuild.")

    records, class_counts, missing_labels, repaired_boxes = find_records(config)
    train_records, validation_records = split_records(records, config.seed, config.val_ratio)
    config.data_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{config.data_dir.name}-", dir=config.data_dir.parent))
    try:
        for split_name, split_records_ in (("train", train_records), ("val", validation_records)):
            for record in with_progress(split_records_, len(split_records_), f"Preparing {split_name}"):
                assert isinstance(record, ImageRecord)
                link_or_copy(record.image_path, staging_dir / "images" / split_name / record.image_path.name)
                if record.label_path is not None:
                    staged_label = staging_dir / "labels" / split_name / record.label_path.name
                    if record.normalized_label is None:
                        link_or_copy(record.label_path, staged_label)
                    else:
                        staged_label.parent.mkdir(parents=True, exist_ok=True)
                        staged_label.write_text(record.normalized_label, encoding="utf-8")

        # data.yaml must retain the final path after the staging directory is renamed.
        write_data_yaml(config, staging_dir / "data.yaml")
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_dir": str(config.dataset_dir.resolve()),
            "seed": config.seed,
            "validation_ratio": config.val_ratio,
            "image_count": len(records),
            "train_image_count": len(train_records),
            "validation_image_count": len(validation_records),
            "background_image_count": missing_labels,
            "boundary_clipped_box_count": repaired_boxes,
            "class_counts": {DEFECT_NAMES[class_id]: class_counts[class_id] for class_id in range(len(DEFECT_NAMES))},
        }
        (staging_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        replace_directory(staging_dir, config.data_dir)
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise

    summary = ", ".join(f"{DEFECT_NAMES[class_id]}={class_counts[class_id]}" for class_id in range(len(DEFECT_NAMES)))
    print(
        f"[dataset] Prepared {len(records)} images: train={len(train_records)}, val={len(validation_records)}, "
        f"background={missing_labels}, boundary_clipped_boxes={repaired_boxes}; labels: {summary}"
    )


def resolve_device(requested_device: str) -> str:
    if requested_device != "auto":
        return requested_device
    try:
        import torch
    except ImportError:
        return "cpu"
    return "0" if torch.cuda.is_available() else "cpu"


def should_patch_nms(mode: str, device: str) -> bool:
    if mode == "off" or device == "cpu":
        return False
    if mode == "always":
        return True
    try:
        import torch
    except ImportError:
        return False
    return device not in {"cpu", "mps"} and torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 10


def patch_torchvision_nms() -> None:
    """Use torchvision's CPU NMS kernel when a new CUDA architecture lacks one."""
    try:
        import torchvision
    except ImportError as exc:
        raise RuntimeError("torchvision is required when CPU NMS fallback is enabled") from exc
    if getattr(torchvision.ops, "_quality_cpu_nms_patched", False):
        return

    original_nms = torchvision.ops.nms

    def nms_via_cpu(boxes: Tensor, scores: Tensor, iou_threshold: float) -> Tensor:
        # torchvision dispatches the saved function to its C++ CPU kernel for CPU tensors.
        boxes_cpu = boxes.detach().float().contiguous().cpu()
        scores_cpu = scores.detach().float().contiguous().cpu()
        return original_nms(boxes_cpu, scores_cpu, iou_threshold).to(boxes.device)

    torchvision.ops.nms = nms_via_cpu
    torchvision.ops.boxes.nms = nms_via_cpu
    torchvision.ops._quality_cpu_nms_patched = True
    print("[train] Enabled torchvision CPU NMS fallback for this process")


def extract_metrics(results: object) -> dict[str, float]:
    result_dict = getattr(results, "results_dict", {}) or {}
    metrics: dict[str, float] = {}
    for key in ("metrics/mAP50(B)", "metrics/mAP50-95(B)", "metrics/precision(B)", "metrics/recall(B)"):
        value = result_dict.get(key)
        if isinstance(value, (int, float)) and math.isfinite(value):
            metrics[key] = float(value)
    return metrics


def validation_epochs(total_epochs: int, interval: int) -> tuple[int, ...]:
    """Return cumulative epoch targets so validation happens at a fixed interval."""
    targets = list(range(interval, total_epochs + 1, interval))
    if not targets or targets[-1] != total_epochs:
        targets.append(total_epochs)
    return tuple(targets)


def make_periodic_validation_trainer() -> type[object]:
    """Create a trainer compatible with resumable 10-epoch validation segments."""
    from ultralytics.models.yolo.detect import DetectionTrainer

    class PeriodicValidationTrainer(DetectionTrainer):
        def check_resume(self, overrides: dict[str, object]) -> None:
            super().check_resume(overrides)
            # Ultralytics normally restores epochs from the checkpoint. Segmented
            # training needs the cumulative target supplied by this invocation.
            if self.resume and "epochs" in overrides:
                self.args.epochs = int(overrides["epochs"])

        def final_eval(self) -> None:
            # The final epoch of every segment has already been validated. Avoid
            # the framework's extra best-model validation after each segment.
            return

    return PeriodicValidationTrainer


@contextmanager
def configure_training_console(verbose: bool, progress_width: int) -> Iterable[None]:
    """Keep useful training progress while suppressing Ultralytics startup noise."""
    import ultralytics.engine.trainer as trainer_module
    from ultralytics.utils import LOGGER

    original_tqdm = trainer_module.TQDM
    original_log_level = LOGGER.level

    class WideProgressBar(original_tqdm):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["disable"] = False
            super().__init__(*args, **kwargs)

        def _generate_bar(self, width: int = progress_width) -> str:
            return super()._generate_bar(width)

    trainer_module.TQDM = WideProgressBar
    if not verbose:
        LOGGER.setLevel(logging.WARNING)
    try:
        yield
    finally:
        trainer_module.TQDM = original_tqdm
        LOGGER.setLevel(original_log_level)


def publish_model(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Training did not produce best.pt: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_suffix(f"{destination.suffix}.tmp")
    shutil.copy2(source, temporary_destination)
    temporary_destination.replace(destination)
    print(f"[train] Published model: {destination}")


def train(config: TrainingConfig, reuse_existing: bool) -> dict[str, float]:
    if not config.base_model.is_file():
        raise FileNotFoundError(f"Base model does not exist: {config.base_model}")
    if not config.data_yaml.is_file():
        raise FileNotFoundError(f"Dataset configuration does not exist: {config.data_yaml}")

    best_model = config.run_dir / "weights" / "best.pt"
    if best_model.is_file() and reuse_existing:
        print(f"[train] Reusing existing training run: {config.run_dir}.")
        publish_model(best_model, config.model_output)
        return {}

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("ultralytics is not installed. Install the vision dependency with: pip install -e backend[vision]") from exc

    device = resolve_device(config.device)
    if "," in device:
        raise RuntimeError("Periodic validation currently supports one training device only")
    if should_patch_nms(config.nms_fallback, device):
        patch_torchvision_nms()
    print(
        f"[train] Starting: epochs={config.epochs}, imgsz={config.image_size}, batch={config.batch}, "
        f"workers={config.workers}, device={device}, validation_interval={config.validation_interval}"
    )
    trainer = make_periodic_validation_trainer()
    validation_metrics: list[dict[str, float]] = []
    best_score = float("-inf")
    with configure_training_console(config.verbose, config.progress_width):
        for segment_index, target_epoch in enumerate(validation_epochs(config.epochs, config.validation_interval), start=1):
            resume = segment_index > 1
            model_path = best_model.parent / "last.pt" if resume else config.base_model
            print(f"[train] Segment {segment_index}: train through epoch {target_epoch}; validation will run at the end")
            model = YOLO(str(model_path))
            results = model.train(
                data=str(config.data_yaml),
                epochs=target_epoch,
                imgsz=config.image_size,
                batch=config.batch,
                device=device,
                project=str(config.runs_dir),
                name=config.run_name,
                exist_ok=True,
                seed=config.seed,
                workers=config.workers,
                val=False,
                resume=resume,
                trainer=trainer,
                verbose=config.verbose,
                plots=False,
            )
            metrics = extract_metrics(results)
            if metrics:
                validation_metrics.append(metrics)
                score = metrics.get("metrics/mAP50-95(B)", float("-inf"))
                is_best = score >= best_score
                best_score = max(best_score, score)
                formatted_metrics = ", ".join(f"{key}={value:.4f}" for key, value in metrics.items())
                print(f"[validation] epoch={target_epoch}, {formatted_metrics}" + (" [best]" if is_best else ""))
    publish_model(best_model, config.model_output)
    if not validation_metrics:
        return {}
    return max(validation_metrics, key=lambda metrics: metrics.get("metrics/mAP50-95(B)", float("-inf")))


def parse_sample_label(label_path: Path) -> tuple[int, float] | None:
    if not label_path.is_file():
        return None
    rows = [line.split() for line in label_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) != 5:
        return None
    try:
        class_id = int(rows[0][0])
        width, height = float(rows[0][3]), float(rows[0][4])
    except ValueError:
        return None
    if not 0 <= class_id < len(DEFECT_NAMES) or width <= 0 or height <= 0:
        return None
    return class_id, width * height


def copy_samples(config: TrainingConfig) -> None:
    candidates: dict[str, list[tuple[float, Path]]] = {}
    for label_path in (config.data_dir / "labels" / "train").glob("*.txt"):
        parsed = parse_sample_label(label_path)
        if parsed is None:
            continue
        class_id, area = parsed
        if area >= 0.03:
            candidates.setdefault(DEFECT_NAMES[class_id], []).append((area, label_path))
    if not candidates:
        print("[samples] No suitable single-defect images found; sample copy skipped")
        return

    selected: list[tuple[str, Path]] = []
    for defect_name in SAMPLE_CLASSES:
        if defect_name in candidates:
            selected.append((defect_name, max(candidates[defect_name], key=lambda item: item[0])[1]))
    if not selected:
        defect_name = next(iter(candidates))
        selected.append((defect_name, max(candidates[defect_name], key=lambda item: item[0])[1]))

    image_by_stem = {path.stem: path for path in (config.data_dir / "images" / "train").iterdir() if path.is_file()}
    config.samples_dir.mkdir(parents=True, exist_ok=True)
    for index, (defect_name, label_path) in enumerate(selected, start=1):
        source = image_by_stem.get(label_path.stem)
        if source is None:
            continue
        destination = config.samples_dir / f"quality_{index}_{defect_name}.jpg"
        if source.suffix.lower() in {".jpg", ".jpeg"}:
            shutil.copy2(source, destination)
        else:
            try:
                from PIL import Image
            except ImportError as exc:
                raise RuntimeError("Pillow is required to convert sample images to JPEG") from exc
            with Image.open(source) as image:
                image.convert("RGB").save(destination, "JPEG", quality=95)
        print(f"[samples] Copied {source.name} to {destination.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare MBDD data and train a YOLO quality model")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--base-model", type=Path, default=DEFAULT_BASE_MODEL)
    parser.add_argument("--model-output", type=Path, default=DEFAULT_MODEL_OUTPUT)
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--run-name", default="quality_mbdd")
    parser.add_argument("--seed", type=int, default=20250805)
    parser.add_argument("--val-ratio", type=ratio, default=0.1)
    parser.add_argument("--epochs", type=positive_int, default=50)
    parser.add_argument("--imgsz", type=positive_int, default=640)
    parser.add_argument("--batch", type=positive_int, default=48, help="Training batch size; lower it only if CUDA reports OOM")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--val-interval", type=positive_int, default=10, help="Run validation every N epochs")
    parser.add_argument("--progress-width", type=positive_int, default=24, help="Visible width of the batch progress bar")
    parser.add_argument("--verbose", action="store_true", help="Show full Ultralytics initialization logs")
    parser.add_argument("--device", default="auto", help="Ultralytics device value; default selects CUDA when available")
    parser.add_argument("--nms-fallback", choices=("auto", "always", "off"), default="auto")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the dataset split")
    parser.add_argument("--reuse-train", action="store_true", help="Reuse an existing best.pt instead of training")
    parser.add_argument("--force-train", action="store_false", dest="reuse_train", help="Compatibility option; training is already the default")
    parser.add_argument("--skip-train", action="store_true", help="Only prepare the dataset and sample images")
    parser.add_argument("--validate-only", action="store_true", help="Validate source images and labels without writing files")
    return parser


def config_from_args(args: argparse.Namespace) -> TrainingConfig:
    if args.workers < 0:
        raise ValueError("--workers cannot be negative")
    return TrainingConfig(
        dataset_dir=args.dataset_dir.resolve(),
        data_dir=args.data_dir.resolve(),
        base_model=args.base_model.resolve(),
        model_output=args.model_output.resolve(),
        samples_dir=args.samples_dir.resolve(),
        runs_dir=args.runs_dir.resolve(),
        run_name=args.run_name,
        seed=args.seed,
        val_ratio=args.val_ratio,
        epochs=args.epochs,
        image_size=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        nms_fallback=args.nms_fallback,
        validation_interval=args.val_interval,
        verbose=args.verbose,
        progress_width=args.progress_width,
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = config_from_args(args)
        if args.validate_only:
            records, class_counts, missing_labels, repaired_boxes = find_records(config)
            print(
                f"[dataset] Validated {len(records)} images, {missing_labels} background images, "
                f"{sum(class_counts.values())} boxes, {repaired_boxes} boxes requiring boundary clipping"
            )
            return 0
        prepare_dataset(config, rebuild=args.rebuild)
        metrics = {} if args.skip_train else train(config, reuse_existing=args.reuse_train)
        copy_samples(config)
        for key, value in metrics.items():
            print(f"[metrics] {key}={value:.4f}")
        print(f"[done] Model output: {config.model_output}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
