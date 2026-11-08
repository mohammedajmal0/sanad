"""The permission filter is the only row security the index has, so it is tested here."""

import pytest

from retrieval.search import build_filters


def test_reader_sees_policies_plus_own_departments():
    assert build_filters("section", ("it",)) == {"strategy": "section", "audience": ["all", "it"]}


def test_no_departments_means_policies_only():
    assert build_filters("fixed") == {"strategy": "fixed", "audience": ["all"]}


def test_unknown_strategy_fails_loudly():
    with pytest.raises(ValueError):
        build_filters("semantic")  # the old name; would otherwise return nothing, silently
