"""Glossary: one source for the app and the README. Also checks the in-app guide."""

from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from scouting.config import load_settings
from scouting.glossary import GLOSSARY, entries
from test_pages import ROOT, app_env  # noqa: F401  (fixture)


def test_every_term_has_both_languages() -> None:
    for item in GLOSSARY:
        assert set(item.term) == {"en", "pt"} and set(item.text) == {"en", "pt"}
    en, pt = entries(load_settings(), "en"), entries(load_settings(), "pt")
    assert len(en) == len(pt) == len(GLOSSARY)
    assert all("{" not in text for _, text in en + pt)  # every placeholder filled


def test_numbers_come_from_the_configuration() -> None:
    settings = load_settings()
    stricter = settings.model_copy(
        update={"analysis": settings.analysis.model_copy(update={"min_minutes": 1350})}
    )
    regular = dict(entries(stricter, "en"))["Regular"]
    assert "1,350 league minutes" in regular and "about 15 full games" in regular
    assert "1.350 minutos" in dict(entries(stricter, "pt"))["Titular habitual"]


def test_readme_glossary_matches_the_app() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Glossary", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"^- \*\*(.+?)\*\*: (.+)$", section, flags=re.MULTILINE)
    assert listed == entries(load_settings(), "en"), (
        "README glossary differs from src/scouting/glossary.py; regenerate it from entries()"
    )


def test_glossary_in_the_sidebar_and_guide_on_the_overview(app_env: Path) -> None:  # noqa: F811
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert any(label.startswith("Glossary") for label in labels)
    assert any(label.startswith("New here?") for label in labels)
    guide = next(e for e in at.expander if e.label.startswith("New here?"))
    assert len(guide.get("page_link")) == 6


def test_end_page_inside_and_outside_the_router(monkeypatch) -> None:
    import pytest

    from scouting.ui import flow

    stopped = []
    monkeypatch.setattr(flow.st, "stop", lambda: stopped.append(True))
    with flow.routed():
        flow.end_page()  # caught by routed(): nothing propagates
        raise AssertionError("not reached")  # pragma: no cover
    assert stopped == []
    with pytest.raises(AssertionError, match="st.stop"):
        flow.end_page()  # outside the router it falls back to st.stop()
    assert stopped == [True]
