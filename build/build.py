#!/usr/bin/env python3
"""Rakentaa site/data.json:n kolmesta kerroksesta:

1. data/events.json  – Ylen kausilista (käsin ylläpidetty)
2. FIS iCal          – kisapäivät
3. Telkku            – lähetysten kellonajat ja kanavat (~2 vk eteenpäin)

Jos FIS tai Telkku ei vastaa, käytetään edellisen julkaistun data.jsonin tietoja
(hallittu heikkeneminen), joten sivu ei koskaan tyhjene.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "sources"))

from classify import Classifier  # noqa: E402
import fis  # noqa: E402
import telkku  # noqa: E402
from net import fetch  # noqa: E402

MATCH_TOLERANCE = timedelta(days=1)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_previous(out_path: Path, site_url: str) -> dict:
    if out_path.exists():
        try:
            return load_json(out_path)
        except Exception as exc:  # noqa: BLE001
            print(f"VAROITUS: paikallista data.jsonia ei voitu lukea: {exc}", file=sys.stderr)
    if site_url:
        try:
            return json.loads(fetch(site_url.rstrip("/") + "/data.json", retries=2))
        except Exception as exc:  # noqa: BLE001
            print(f"HUOM: edellistä julkaistua dataa ei saatu ({exc})", file=sys.stderr)
    return {}


def in_event_window(day: date, event: dict) -> bool:
    start = date.fromisoformat(event["start"]) - MATCH_TOLERANCE
    end = date.fromisoformat(event["end"]) + MATCH_TOLERANCE
    return start <= day <= end


def mentions(text: str, aliases: list[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"(?<!\w){re.escape(a.lower())}", low) for a in aliases)


def match_event(events: list[dict], sport: str, day: date, text: str) -> str | None:
    candidates = [e for e in events if e["sport"] == sport and in_event_window(day, e)]
    named = [e for e in candidates if mentions(text, e.get("aliases", [e["place"]]))]
    if named:
        return named[0]["id"]
    if len(candidates) == 1:
        return candidates[0]["id"]
    return None


TDS_RE = re.compile(r"\bTour de Ski\b[,:]?\s*", re.IGNORECASE)


def clean_title(title: str, event: dict | None) -> str:
    """TV-oppaan otsikoissa lukee välillä "Tour de Ski" myös tavallisissa maailmancupin kisoissa
    (esim. Ruka). Merkintä poistetaan, ellei tapahtumaa ole merkitty events.jsonissa Tour de Skiksi."""
    if event is not None and not event.get("tour_de_ski"):
        title = TDS_RE.sub("", title)
        title = re.sub(r":\s*$", "", title).strip()
    return title


def build_broadcasts(programs: list[dict], cfg: dict, classifier: Classifier,
                     topics_by_id: dict, events: list[dict], tz: ZoneInfo) -> list[dict]:
    channels = cfg["channels"]
    out = []
    for p in programs:
        if p.get("format") != "SPORT" or p.get("broadcastType") != "live":
            continue
        title = (p.get("programName") or "").strip()
        topic = classifier.classify(title)
        if not topic:
            continue
        start = datetime.fromisoformat(p["startTime"].replace("Z", "+00:00")).astimezone(tz)
        end = datetime.fromisoformat(p["endTime"].replace("Z", "+00:00")).astimezone(tz)
        desc = (p.get("description") or "").strip()
        ch = channels.get(p["channelId"], {})
        event_id = match_event(events, topics_by_id[topic]["event_sport"], start.date(), f"{title} {desc}")
        event = next((e for e in events if e["id"] == event_id), None)
        out.append({
            "id": f'telkku-{p["channelId"]}-{p.get("id") or p["startTime"]}',
            "topic": topic,
            "event_id": event_id,
            "channel": ch.get("name", p["channelId"]),
            "live_url": ch.get("live_url"),
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "title": clean_title(title, event),
            "description": desc[:400],
        })
    out.sort(key=lambda b: (b["start"], b["channel"]))
    return out


def has_ski_leg(name: str) -> bool:
    """Yhdistetystä näytetään vain kisat, joissa on hiihto-osuus (ei pelkkiä mäkikierroksia)."""
    return bool(re.search(r"\d\s*km", name, re.IGNORECASE))


RACE_KEYS = ("date", "discipline", "gender", "name_fi", "url")
WC_CATEGORIES = {"World Cup", "Stage World Cup"}


def attach_races(events: list[dict], races: list[dict]) -> tuple[dict[str, list[dict]], set[str]]:
    """Liittää FIS-kisat Ylen tapahtumiin. Palauttaa (kisat tapahtumittain, liitettyjen kisojen uid:t)."""
    by_event: dict[str, list[dict]] = {}
    used: set[str] = set()
    for e in events:
        if e["sport"] != "hiihto":
            continue
        aliases = e.get("aliases", [e["place"]])
        matched = [r for r in races
                   if (r["discipline"] == "CC" or (r["discipline"] == "NK" and has_ski_leg(r["name"])))
                   and in_event_window(date.fromisoformat(r["date"]), e)
                   and mentions(r["place"], aliases)]
        if matched:
            matched.sort(key=lambda r: (r["date"], r["discipline"], r["gender"], r["name"]))
            by_event[e["id"]] = [{k: r[k] for k in RACE_KEYS} for r in matched]
            used.update(r["uid"] for r in matched)
    return by_event, used


def non_yle_events(races: list[dict], used: set[str]) -> list[dict]:
    """Maastohiihdon maailmancupin kisat, joita ei ole Ylen listalla, ryhmiteltynä tapahtumiksi.
    Tour de Skin osakilpailut (FIS: "Stage World Cup") kootaan yhdeksi tapahtumaksi."""
    pool = [r for r in races
            if r["discipline"] == "CC" and r["category"] in WC_CATEGORIES
            and r["uid"] not in used and not r["place"].lower().startswith("fis tour de ski")]
    groups: list[dict] = []
    for r in sorted(pool, key=lambda r: (r["date"], r["place"])):
        tds = r["category"] == "Stage World Cup"
        key = "Tour de Ski" if tds else r["place"]
        d = date.fromisoformat(r["date"])
        g = next((g for g in groups if g["key"] == key
                  and (d - date.fromisoformat(g["end"])).days <= (10 if tds else 3)), None)
        if g is None:
            g = {"key": key, "tds": tds, "start": r["date"], "end": r["date"], "places": [], "races": []}
            groups.append(g)
        g["end"] = max(g["end"], r["date"])
        if r["place"] not in g["places"]:
            g["places"].append(r["place"])
        g["races"].append(r)
    out = []
    for g in groups:
        g["races"].sort(key=lambda r: (r["date"], r["gender"], r["name"]))
        place = g["key"].split("/")[0]
        out.append({
            "id": f'fis-{re.sub(r"[^a-z0-9]+", "-", place.lower()).strip("-")}-{g["start"]}',
            "sport": "hiihto", "type": "MC", "place": place, "start": g["start"], "end": g["end"],
            "broadcaster": "other",
            "note": ("Osakilpailut: " + ", ".join(g["places"]) + ". " if g["tds"] else "")
                    + "Ei Ylen ohjelmistossa – maailmancupin kisat näytetään Viaplayssa.",
            "races": [{k: r[k] for k in RACE_KEYS} for r in g["races"]],
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "site" / "data.json"))
    ap.add_argument("--offline", action="store_true", help="älä hae verkosta (käytä edellistä dataa)")
    args = ap.parse_args()

    sources = load_json(ROOT / "config" / "sources.json")
    topics_cfg = load_json(ROOT / "config" / "topics.json")
    season = load_json(ROOT / "data" / "events.json")
    events = season["events"]
    tz = ZoneInfo(sources["timezone"])
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out_path = Path(args.out)

    prev = load_previous(out_path, sources.get("site_url", ""))
    prev_status = prev.get("status", {})
    status = {}

    # --- Kerros 3: Telkku-lähetykset ---------------------------------------
    classifier = Classifier(topics_cfg)
    topics_by_id = {t["id"]: t for t in topics_cfg["topics"]}
    try:
        if args.offline:
            raise RuntimeError("offline-tila")
        programs, total = telkku.fetch_programs(sources["telkku"], today_start)
        if total == 0:
            raise RuntimeError("Telkku palautti 0 ohjelmaa – rajapinta muuttunut?")
        broadcasts = build_broadcasts(programs, sources["telkku"], classifier, topics_by_id, events, tz)
        status["telkku"] = {"ok": True, "updated": now.isoformat(timespec="minutes"), "programs_seen": total}
    except Exception as exc:  # noqa: BLE001
        print(f"VAROITUS: Telkku epäonnistui, käytetään edellistä dataa: {exc}", file=sys.stderr)
        cutoff = (now - timedelta(days=2)).isoformat()
        broadcasts = [b for b in prev.get("broadcasts", []) if b.get("end", "") >= cutoff]
        status["telkku"] = {"ok": False, "error": str(exc)[:200],
                            "updated": prev_status.get("telkku", {}).get("updated")}

    # --- Kerros 2: FIS-kisat ---------------------------------------------------
    try:
        if args.offline:
            raise RuntimeError("offline-tila")
        all_races = fis.fetch_races(sources["fis"])
        races_by_event, used = attach_races(events, all_races)
        other_events = non_yle_events(all_races, used)
        status["fis"] = {"ok": True, "updated": now.isoformat(timespec="minutes")}
    except Exception as exc:  # noqa: BLE001
        print(f"VAROITUS: FIS epäonnistui, käytetään edellistä dataa: {exc}", file=sys.stderr)
        races_by_event = {e["id"]: e.get("races", []) for e in prev.get("events", []) if e.get("races")}
        other_events = [e for e in prev.get("events", []) if e.get("broadcaster") == "other"]
        status["fis"] = {"ok": False, "error": str(exc)[:200],
                         "updated": prev_status.get("fis", {}).get("updated")}

    # --- Kokoa ---------------------------------------------------------------
    out_events = []
    for e in sorted(events, key=lambda e: (e["start"], e["sport"])):
        item = {k: e[k] for k in ("id", "sport", "type", "place", "start", "end")}
        item["broadcaster"] = "yle"
        if e.get("note"):
            item["note"] = e["note"]
        item["races"] = races_by_event.get(e["id"], [])
        out_events.append(item)
    out_events = sorted(out_events + other_events, key=lambda e: (e["start"], e["broadcaster"] != "yle", e["sport"]))

    order = topics_cfg.get("display_order", [])
    data = {
        "generated": now.isoformat(timespec="minutes"),
        "season": season["season"],
        "source": season["source"],
        "status": status,
        "horizon_days": sources["telkku"]["days_ahead"],
        "topics": [{"id": t["id"], "label": t["label"], "event_sport": t["event_sport"]}
                   for t in sorted(topics_cfg["topics"], key=lambda t: order.index(t["id"]) if t["id"] in order else 99)],
        "events": out_events,
        "broadcasts": broadcasts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n_races = sum(len(v) for v in races_by_event.values())
    print(f"OK: {len(out_events) - len(other_events)} Ylen tapahtumaa + {len(other_events)} muuta, {n_races} kisaa, {len(broadcasts)} lähetystä → {out_path}")
    print(f"    Telkku: {'ok' if status['telkku']['ok'] else 'VANHA DATA'}, FIS: {'ok' if status['fis']['ok'] else 'VANHA DATA'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
