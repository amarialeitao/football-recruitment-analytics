"""Ending a page early without losing the shared sidebar footer.

``st.stop()`` ends the whole script run, so anything the router draws after the page (the
glossary and the disclaimer at the bottom of the sidebar) would disappear on pages that stop
early, such as an empty shortlist or a search with no results. Pages call :func:`end_page`
instead. When the router in ``app.py`` is running the page (:func:`routed`), it raises
:class:`EndPage`, which the router catches before drawing the footer. When a page runs on its
own (for example in some test harnesses), it falls back to ``st.stop()``.

The flag is a context variable, so concurrent sessions (each script run has its own thread)
never see each other's state.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import NoReturn

import streamlit as st

_ROUTED: ContextVar[bool] = ContextVar("scouting_routed", default=False)


class EndPage(Exception):  # noqa: N818  (a signal, not an error)
    """Raised to end the current page; caught by :func:`routed`."""


@contextmanager
def routed() -> Iterator[None]:
    """Run a page through the router: pages that end early do not end the router's script."""
    token = _ROUTED.set(True)
    try:
        yield
    except EndPage:
        pass  # the page ended early on purpose (empty list, no results, missing data)
    finally:
        _ROUTED.reset(token)


def end_page() -> NoReturn:
    if _ROUTED.get():
        raise EndPage
    st.stop()
    raise AssertionError("st.stop() returned")  # pragma: no cover  (keeps NoReturn honest)
