from __future__ import annotations

import shutil
from pathlib import Path


def create_annotated_copy(source: Path, destination_dir: Path, name: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / name
    shutil.copyfile(source, destination)
    return destination
