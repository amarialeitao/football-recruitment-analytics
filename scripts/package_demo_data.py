"""Package the processed data as a zip for the hosted demo (attach it to a GitHub release).

Usage:
    python scripts/package_demo_data.py              # writes data/demo/demo-data.zip

Then upload the zip to a release and set ``sources.demo_data.url`` and ``sha256`` in
config/settings.yaml to the values printed below. See README > Live demo.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scouting.config import load_settings
from scouting.ingest.demo_data import package
from scouting.ingest.transfermarkt import sha256_of


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    out = args.out or settings.resolve(Path("data/demo/demo-data.zip"))
    package(settings.processed_dir, out)
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"sha256: {sha256_of(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
