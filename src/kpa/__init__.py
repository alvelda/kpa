"""
KPA — Keynote Programmatic Authoring
====================================

Open-source Python toolkit for reading, writing, authoring, editing,
and optimizing Apple Keynote (`.key`) presentations.

This is the **Step 4a** scaffolding — minimal public API surface, no
authoring yet. Step 4b adds mutation; Step 4c adds brand-compliance
and asset grovel; Step 4d adds the CLI DSL and F2/F2b/F2c gates.

Quick reference:

    >>> import kpa
    >>> deck = kpa.open("recon/svef.key")        # load existing deck
    >>> deck.save("out.key")                     # round-trip
    >>> deck.summary()                            # text summary

    >>> # Step 4b+:
    >>> deck = kpa.Deck.from_template("recon/svef.key")
    >>> deck.slide[3].title.set_text("New title")
    >>> deck.slide[3].title.move(dy="20%")
    >>> deck.save("edited.key")

License: MIT. See LICENSE.
"""

from __future__ import annotations

from kpa._version import __version__
from kpa.deck import Deck, open  # noqa: A004  (deliberately shadow builtins.open in module scope only)

__all__ = ["Deck", "open", "__version__"]
