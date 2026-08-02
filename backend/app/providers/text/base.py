from __future__ import annotations

from typing import Protocol


class TextProvider(Protocol):
    def generate_worker_message(self, payload: dict[str, object]) -> str:
        ...

    def generate_report(self, payload: dict[str, object]) -> str:
        ...
