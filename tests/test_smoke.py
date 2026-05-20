"""Phase 0 smoke test: the package and engine import."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_package_imports() -> None:
    import dialectical_checkers

    assert dialectical_checkers is not None


@pytest.mark.unit
def test_engine_imports_and_constructs() -> None:
    from dialectical_checkers import DialecticalCheckersEngine

    engine = DialecticalCheckersEngine()
    assert engine is not None
