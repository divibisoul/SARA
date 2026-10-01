from __future__ import annotations

import pytest

from sara.meta.n02_external_capability import N02ExternalCapabilityAdapter


def test_requires_valid_n07_endpoint() -> None:
    with pytest.raises(ValueError, match="http/https"):
        N02ExternalCapabilityAdapter("n07.invalid")
