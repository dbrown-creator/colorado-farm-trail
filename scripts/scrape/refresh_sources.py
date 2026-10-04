"""Check the network sources for new data and save snapshots. Run on purpose, not per build.

  python scripts/scrape/refresh_sources.py                  # every source
  python scripts/scrape/refresh_sources.py cfma usda_api    # just these

Sources: colorado_proud, cfma, chaffee_provides, usda_api, usda_datashare.
Each writes source-data/phase2/snapshots/<source>.json (what build.py reads, offline)
and snapshots/changes/<source>.csv: what's new, removed or changed versus the previous
snapshot. Review that report, then commit the snapshot (= approve) and build. A source
that fails keeps its previous snapshot.

Chaffee Provides goes through its page cache (7-day reuse; CHAFFEE_REFRESH=1 forces a
full ~8-minute polite recrawl). USDA reads USDA_API_KEY from the repo .env (no key ->
usda_api is skipped); narrow directories with USDA_DIRECTORIES=csa,foodhub.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrape import snapshots
from scrape.build import load_env
from scrape.sources import cfma, chaffee_provides, colorado_proud, usda


def _usda_dirs():
    return [d.strip() for d in os.environ.get("USDA_DIRECTORIES", "").split(",") if d.strip()] or None


def _usda_api():
    key = os.environ.get("USDA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("USDA_API_KEY not set (add it to .env); skipping keyed API")
    return usda.fetch_api(key, _usda_dirs())


FETCHERS = {
    "colorado_proud": colorado_proud.fetch,
    "cfma": cfma.fetch,
    "chaffee_provides": chaffee_provides.fetch,
    "usda_api": _usda_api,
    # data_share is not a strict subset of the keyed view, so it's kept as a gap-filler.
    "usda_datashare": lambda: usda.fetch_datashare(_usda_dirs()),
}


def refresh(names, fetchers=FETCHERS, snapshot_dir: str = snapshots.SNAPSHOT_DIR) -> dict:
    """Fetch each named source and save its snapshot. -> {name: count or error str}."""
    result = {}
    for name in names:
        if name not in fetchers:
            result[name] = f"unknown source (choose from {', '.join(fetchers)})"
            continue
        print(f"{name}...", flush=True)
        try:
            recs = fetchers[name]()
        except Exception as e:  # keep the previous snapshot
            result[name] = f"failed, kept previous snapshot: {e}"
            print(f"  {result[name]}")
            continue
        previous, _ = snapshots.load(name, snapshot_dir)
        changes = snapshots.diff(previous, recs)
        snapshots.save(name, recs, snapshot_dir)
        report = snapshots.write_changes(name, changes, os.path.join(snapshot_dir, "changes"))
        result[name] = len(recs)
        counts = {c: sum(1 for r in changes if r["change"] == c) for c in ("new", "changed", "removed")}
        print(f"  {len(recs)} records; {counts['new']} new, {counts['removed']} removed, "
              f"{len({r['key'] for r in changes if r['change'] == 'changed'})} changed -> review {report}")
    return result


def main(argv=None) -> None:
    load_env()
    names = (argv if argv is not None else sys.argv[1:]) or snapshots.NETWORK_SOURCES
    refresh(names)


if __name__ == "__main__":
    main()
