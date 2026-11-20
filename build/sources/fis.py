"""FIS:n virallinen iCal-kalenterisyöte → kisalista."""
import re
import urllib.parse

from ical import parse_events
from net import fetch

GENDER_FI = {"men": "M", "women": "N", "mixed": "Seka", "ladies": "N"}

# Järjestys merkitsee: pidemmät fraasit ensin.
NAME_FI = [
    ("Team Sprint Qualification", "parisprintin karsinta"),
    ("Team Sprint", "parisprintti"),
    ("Sprint Qualification", "sprintin karsinta"),
    ("Sprint Final", "sprintin finaalit"),
    ("Individual Mass Start", "yhteislähtö"),
    ("Interval Start", "väliaikalähtö"),
    ("Mass Start", "yhteislähtö"),
    ("Skiathlon", "yhdistelmähiihto"),
    ("Pursuit", "takaa-ajo"),
    ("Relay", "viesti"),
    ("Individual Gundersen", "Gundersen"),
    ("Individual Compact", "Compact"),
    ("Normal Hill", "normaalimäki"),
    ("Large Hill", "suurmäki"),
    ("Classic/Free", "(p/v)"),
    ("Classic", "(p)"),
    ("Free", "(v)"),
    ("Team", "joukkue"),
]


def translate_name(name: str) -> str:
    out = name
    for en, fi in NAME_FI:
        out = re.sub(rf"\b{re.escape(en)}\b", fi, out)
    out = re.sub(r"(\d)\.(\d)", r"\1,\2", out)          # 1.4km → 1,4km
    out = re.sub(r"(\d)km\b", r"\1 km", out)             # 10km → 10 km
    return re.sub(r"\s+", " ", out).strip()


def feed_url(cfg: dict, feed: dict) -> str:
    params = {"seasoncode": cfg["season"], "sectorcode": feed["sector"], "categorycode": feed["category"]}
    if feed.get("nation"):
        params["nationcode"] = feed["nation"]
    return f'{cfg["base"]}?{urllib.parse.urlencode(params)}'


def parse_races(text: str, sector: str) -> list[dict]:
    races = []
    for ev in parse_events(text):
        dt = ev.get("DTSTART", {}).get("value", "")
        if len(dt) < 8:
            continue
        date = f"{dt[0:4]}-{dt[4:6]}-{dt[6:8]}"
        summary = ev.get("SUMMARY", {}).get("value", "")
        desc = ev.get("DESCRIPTION", {}).get("value", "")
        place = re.sub(r"\s*\([A-Z]{3}\)\s*$", "", summary.split(" - ")[0]).strip()
        category = (re.search(r"Category:\s*([^\n|]+)", desc) or [None, ""])[1].strip()
        gender = (re.search(r"Gender:\s*(\w+)", desc) or [None, ""])[1].strip()
        name = (re.search(r"Event:\s*([^\n]+)", desc) or [None, ""])[1].strip()
        if not name and " - " in summary:
            name = summary.split(" - ", 1)[1]
        url = (re.search(r"Result/Startlist:\s*(\S+)", desc) or [None, ""])[1].strip()
        races.append({
            "uid": ev.get("UID", {}).get("value", "") or f"{sector}-{date}-{name}-{gender}",
            "date": date,
            "discipline": sector,
            "category": category,
            "place": place,
            "gender": GENDER_FI.get(gender.lower(), gender),
            "name": name,
            "name_fi": translate_name(name),
            "url": url,
        })
    return races


def fetch_races(cfg: dict) -> list[dict]:
    """Hakee kaikki konfiguroidut syötteet. Nostaa poikkeuksen, jos jokin syöte epäonnistuu."""
    races: dict[str, dict] = {}
    for feed in cfg["feeds"]:
        text = fetch(feed_url(cfg, feed)).decode("utf-8", errors="replace")
        if "BEGIN:VCALENDAR" not in text:
            raise RuntimeError(f"FIS-syöte ei ole iCal-muotoa: {feed}")
        for r in parse_races(text, feed["sector"]):
            races[r["uid"]] = r
    return list(races.values())
