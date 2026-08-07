"""An append-only, hash-chained transparency log for conformance statements.

Entries are chained: each carries the hash of the one before it, so removing or
altering a past entry breaks every hash after it. That is what makes the log
append-only in fact rather than by policy, and it is why nobody has to be
trusted to operate it honestly.

What the log deliberately does not do:

  It does not decide conformance. Entries record what was claimed and when. The
  lease state a reader sees is computed from the statement against their own
  clock, so the log going quiet cannot keep a badge alive.

  It does not gate verification. A relying party verifies a statement they were
  handed. The log answers "was this published, and has the record been altered
  since?" — a separate and weaker question that still needs an honest answer.

  It does not authenticate the operator. A log with a captured operator can
  refuse to append. It cannot forge a past entry, and it cannot make an expired
  statement look current.

This is a local file implementation. The format is the contract; a hosted log
speaking the same format is a drop-in replacement.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from openaisf.errors import ValidationError
from openaisf.signing import canonical

GENESIS = "sha256:" + "0" * 64


def _entry_hash(index: int, previous: str, statement: dict, appended_at: str) -> str:
    material = canonical(
        {
            "index": index,
            "previous": previous,
            "statement": statement,
            "appended_at": appended_at,
        }
    )
    return "sha256:" + hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class LogEntry:
    index: int
    previous: str
    entry_hash: str
    appended_at: datetime
    statement: dict

    @property
    def system_id(self) -> str:
        return self.statement.get("system_id", "")

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "previous": self.previous,
            "entry_hash": self.entry_hash,
            "appended_at": self.appended_at.isoformat(),
            "statement": self.statement,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        return cls(
            index=data["index"],
            previous=data["previous"],
            entry_hash=data["entry_hash"],
            appended_at=datetime.fromisoformat(data["appended_at"]),
            statement=data["statement"],
        )


class TransparencyLog:
    """Newline-delimited JSON. One entry per line, appended, never rewritten."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def entries(self) -> list[LogEntry]:
        if not self.path.exists():
            return []
        out: list[LogEntry] = []
        for number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                out.append(LogEntry.from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValidationError(
                    f"{self.path.name} line {number}: malformed log entry: {exc}"
                ) from exc
        return out

    def head(self) -> str:
        entries = self.entries()
        return entries[-1].entry_hash if entries else GENESIS

    def append(self, statement: dict, now: datetime | None = None) -> LogEntry:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        existing = self.entries()
        index = len(existing)
        previous = existing[-1].entry_hash if existing else GENESIS
        appended_at = now.isoformat()

        entry = LogEntry(
            index=index,
            previous=previous,
            entry_hash=_entry_hash(index, previous, statement, appended_at),
            appended_at=now,
            statement=statement,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
        return entry

    def verify_chain(self) -> None:
        """Raise if any entry has been altered, removed or reordered."""
        previous = GENESIS
        for position, entry in enumerate(self.entries()):
            if entry.index != position:
                raise ValidationError(
                    f"log entry at position {position} claims index {entry.index}; "
                    f"an entry has been removed or reordered"
                )
            if entry.previous != previous:
                raise ValidationError(
                    f"log entry {entry.index} does not chain to its predecessor; "
                    f"a past entry has been altered"
                )
            expected = _entry_hash(
                entry.index, entry.previous, entry.statement,
                entry.appended_at.isoformat(),
            )
            if expected != entry.entry_hash:
                raise ValidationError(
                    f"log entry {entry.index} hash does not match its content; "
                    f"the entry has been tampered with"
                )
            previous = entry.entry_hash

    def latest_for(self, system_id: str) -> LogEntry | None:
        matching = [e for e in self.entries() if e.system_id == system_id]
        return matching[-1] if matching else None
