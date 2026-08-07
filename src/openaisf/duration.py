"""Parse the ISO-8601 durations used for freshness windows.

Only the subset the catalog uses: whole days, hours, minutes and seconds. Kept
in the standard library deliberately — this runs in other people's CI and the
runtime dependency list is meant to stay at two.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import re
from datetime import timedelta

from openaisf.errors import ValidationError

_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_duration(text: str) -> timedelta:
    """P30D, PT24H, P7DT12H. Raises ValidationError on anything else."""
    match = _PATTERN.match(text or "")
    if not match or text in ("P", "PT"):
        raise ValidationError(
            f"unsupported duration {text!r}; expected an ISO-8601 duration in "
            f"days, hours, minutes or seconds such as P30D or PT24H"
        )
    parts = {k: int(v) for k, v in match.groupdict().items() if v}
    if not parts:
        raise ValidationError(f"duration {text!r} has no components")
    return timedelta(**parts)
