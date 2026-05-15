from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Persist:
    entity: Any


@dataclass(frozen=True)
class Delete:
    entity_type: type
    id: Any


@dataclass(frozen=True)
class Skip:
    reason: str


DbIntent = Persist | Delete | Skip
