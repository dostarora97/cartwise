from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProblemDetailError(Exception):
    type: str
    title: str
    status: int
    detail: str
    extras: dict = field(default_factory=dict)

    def __init__(self, *, type: str, title: str, status: int, detail: str, **extras: object):
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.extras = extras
        super().__init__(detail)

    def to_dict(self) -> dict:
        body = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        body.update(self.extras)
        return body
