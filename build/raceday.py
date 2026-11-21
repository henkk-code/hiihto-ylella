#!/usr/bin/env python3
"""Iltapäivityksen portti: onko tänään maailmancupin tai MM-kisojen kisapäivä?

Lukee edellisen julkaistun data.jsonin ja kirjoittaa GitHub Actionsille `run=true|false`.
Jos dataa ei saada, päivitys ajetaan varmuuden vuoksi.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from net import fetch  # noqa: E402

RACE_TYPES = {"MC", "MM"}


def is_race_day(data: dict, today: str) -> bool:
    """Tosi, jos jokin MC- tai MM-tapahtuma (myös muut kuin Ylen) on käynnissä tänään."""
    for e in data.get("events", []):
        if e.get("type") not in RACE_TYPES:
            continue
        races = e.get("races") or []
        if races:
            if any(r.get("date") == today for r in races):
                return True
        elif e["start"] <= today <= e["end"]:          # esim. ampumahiihto: ei kisatason dataa
            return True
    return False


def main() -> int:
    sources = json.loads((HERE.parent / "config" / "sources.json").read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo(sources["timezone"])).date().isoformat()
    try:
        data = json.loads(fetch(sources["site_url"].rstrip("/") + "/data.json", retries=2))
        run = is_race_day(data, today)
        print(f"{today}: {'kisapäivä → päivitetään' if run else 'ei kisoja → ohitetaan'}")
    except Exception as exc:  # noqa: BLE001
        run = True
        print(f"HUOM: dataa ei saatu ({exc}), päivitetään varmuuden vuoksi")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
