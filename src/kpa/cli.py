"""kpa CLI — Step 4a stub.

Today (4a) supports only:
  - ``kpa unpack <deck.key> [--output DIR]``  — thin alias for keynote-parser unpack
  - ``kpa pack <DIR> [--output deck.key]``    — thin alias for keynote-parser pack
  - ``kpa info <deck.key>``                    — summary of the deck

Step 4d adds:
  - ``kpa author --spec deck.py --template T --out out.key``
  - ``kpa edit <deck.key> '<DSL>'``
  - ``kpa harvest --assets DIR --out LIBRARY`` (Step 4c)
  - ``kpa preview <deck.key> --out preview/`` (Step 6.5)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kpa import Deck, __version__


def cmd_unpack(args):
    import subprocess
    cmd = ["keynote-parser", "unpack", args.path]
    if args.output:
        cmd.extend(["--output", args.output])
    result = subprocess.run(cmd, check=False)
    return result.returncode


def cmd_pack(args):
    import subprocess
    cmd = ["keynote-parser", "pack", args.path]
    if args.output:
        cmd.extend(["--output", args.output])
    result = subprocess.run(cmd, check=False)
    return result.returncode


def cmd_info(args):
    deck = Deck.open(args.path)
    print(deck.summary())
    deck.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kpa",
        description="KPA — Keynote Programmatic Authoring",
    )
    parser.add_argument("--version", action="version", version=f"kpa {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_unpack = sub.add_parser("unpack", help="Unpack a .key into an editable tree")
    p_unpack.add_argument("path")
    p_unpack.add_argument("--output", "-o")
    p_unpack.set_defaults(func=cmd_unpack)

    p_pack = sub.add_parser("pack", help="Pack an unpacked tree back into .key")
    p_pack.add_argument("path")
    p_pack.add_argument("--output", "-o")
    p_pack.set_defaults(func=cmd_pack)

    p_info = sub.add_parser("info", help="Print summary of a .key file")
    p_info.add_argument("path")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
