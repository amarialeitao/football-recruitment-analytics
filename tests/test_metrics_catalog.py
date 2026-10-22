"""Tests for catalog. All values are invented."""

from __future__ import annotations

import pytest

from scouting.metrics import catalog


def test_profile_metrics_are_all_in_catalog() -> None:
    for keys in catalog.PROFILE_METRICS.values():
        for key in keys:
            assert key in catalog.METRICS


def test_unknown_metric_raises_with_known_keys() -> None:
    with pytest.raises(KeyError, match="goals_p90"):
        catalog.metric("xg_p90")
