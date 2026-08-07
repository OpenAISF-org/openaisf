"""Typed errors for the OpenAISF reference implementation."""


class SpecError(Exception):
    """Base class for all specification-loading failures."""


class ValidationError(SpecError):
    """A specification artefact failed schema or invariant validation."""
