"""EvidenceRecord type contracts.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

import typing
from datetime import datetime, timedelta, timezone

from openaisf.evidence import EvidenceRecord


def test_age_returns_a_timedelta():
    record = EvidenceRecord(
        control="D07-C01",
        plane="control",
        system_id="urn:openaisf:system:test",
        window_from=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        window_to=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
        observations={},
        producer="test-adapter",
        producer_version="1.0",
        signature=None,
        verified=False,
        key_known=True,
    )
    resolved = typing.get_type_hints(EvidenceRecord.age)["return"]
    assert resolved is timedelta
    age = record.age(datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc))
    assert isinstance(age, timedelta)
    assert age == timedelta(days=1)