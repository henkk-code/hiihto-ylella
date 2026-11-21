#!/usr/bin/env python3
"""Rakentaa site/data.json:n kolmesta kerroksesta:

1. data/events.json  – Ylen kausilista (käsin ylläpidetty)
2. FIS iCal          – kisapäivät
3. Telkku            – lähetysten kellonajat ja kanavat (~2 vk eteenpäin)
+ maailmancupin pistetilanne (FIS, Wikipedia)
+ maastohiihtäjien profiilit (FIS, Wikidata, Wikipedia)
+ kisojen top 30 -tulokset (FIS; Suomen cup Hiihtoliiton PDF:istä)

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
import athletes  # noqa: E402
import fis  # noqa: E402
import results as race_results  # noqa: E402
import standings  # noqa: E402
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

    # --- Maailmancupin pistetilanne ---------------------------------------------
    st_cfg = dict(sources["standings"], season=sources["fis"]["season"])
    prev_lists = {s["id"]: s for s in prev.get("standings", []) if s.get("season") == st_cfg["season"]}
    try:
        if args.offline:
            raise RuntimeError("offline-tila")
        lists, st_errors = standings.fetch_standings(st_cfg)
    except Exception as exc:  # noqa: BLE001
        lists, st_errors = [], {"kaikki": str(exc)[:200]}
    got = {s["id"] for s in lists}
    for sid, old in prev_lists.items():                      # epäonnistuneet listat edellisestä datasta
        if sid not in got:
            lists.append(old)
    order = {t: i for i, t in enumerate(topics_cfg.get("display_order", []))}
    lists.sort(key=lambda s: (order.get(s["topic"], 99), s["gender"]))
    if st_errors:
        print(f"VAROITUS: pistetilanne osin vanhaa dataa: {st_errors}", file=sys.stderr)
        status["standings"] = {"ok": False, "error": "; ".join(f"{k}: {v}" for k, v in st_errors.items())[:300],
                               "updated": prev_status.get("standings", {}).get("updated")}
    else:
        status["standings"] = {"ok": True, "updated": now.isoformat(timespec="minutes")}

    # --- Hiihtäjäprofiilit (vain maastohiihto) ----------------------------------
    race_names = {}
    for r in [r for rs in races_by_event.values() for r in rs] + [r for e in other_events for r in e.get("races", [])]:
        m = re.search(r"raceid=(\d+)", r.get("url") or "")
        if m and r["discipline"] == "CC":
            race_names[m.group(1)] = r["name_fi"]
    prev_ath = prev.get("athletes", {})
    try:
        if args.offline:
            raise RuntimeError("offline-tila")
        ath, ath_errors = athletes.fetch_profiles(lists, prev_ath, st_cfg["season"], race_names, now,
                                                  athletes.champs_active(events, now.date()))
    except Exception as exc:  # noqa: BLE001
        wanted = {t["id"] for t in athletes.targets(lists)}
        ath, ath_errors = {k: v for k, v in prev_ath.items() if k in wanted}, {"kaikki": str(exc)[:200]}
    if ath_errors:
        print(f"VAROITUS: profiilit osin vanhaa dataa: {ath_errors}", file=sys.stderr)
        status["athletes"] = {"ok": False, "error": "; ".join(f"{k}: {v}" for k, v in ath_errors.items())[:300],
                              "updated": prev_status.get("athletes", {}).get("updated")}
    else:
        status["athletes"] = {"ok": True, "updated": now.isoformat(timespec="minutes")}

    # --- Kisojen top 30 -tulokset ---------------------------------------------
    # Vain kuluvan kauden tulokset: raja on Ylen kausilistan ensimmäisen tapahtuman alku (2026–27: 31.10.2026).
    results_from = min(e["start"] for e in events)
    prev_results = prev.get("results", {})
    res_errors: dict[str, str] = {}
    listed = [r for rs in races_by_event.values() for r in rs if r["date"] >= results_from] + \
             [r for e in other_events for r in e.get("races", []) if r["date"] >= results_from]
    try:
        if args.offline:
            raise RuntimeError("offline-tila")
        results, fis_res_errors = race_results.fetch_fis_results(listed, prev_results, now)
        res_errors.update(fis_res_errors)
    except Exception as exc:  # noqa: BLE001
        results = {k: v for k, v in prev_results.items() if k.startswith("fis-")}
        res_errors["FIS"] = str(exc)[:200]
    prev_sc = {e["id"]: [r for r in e.get("races", []) if r.get("res", "").startswith("sc-")]
               for e in prev.get("events", []) if e.get("type") == "SC"}
    for e in events:
        if e.get("type") != "SC":
            continue
        sc_races = {r["res"]: r for r in prev_sc.get(e["id"], [])}
        sc_res = {k: prev_results[k] for k in sc_races if k in prev_results}
        if not args.offline and race_results.sc_due(e, list(sc_races.values()), now.date(), prev_results):
            try:
                got_races, got_res, errs = race_results.fetch_sc_event(e, now)
                sc_races.update({r["res"]: r for r in got_races})     # uudet korvaavat, vanhat säilyvät
                sc_res.update(got_res)
                if errs:
                    res_errors[e["id"]] = "; ".join(errs)[:200]
            except Exception as exc:  # noqa: BLE001
                res_errors[e["id"]] = str(exc)[:200]
        if sc_races:
            fis_races = [r for r in races_by_event.get(e["id"], []) if not r.get("res", "").startswith("sc-")]
            races_by_event[e["id"]] = sorted(fis_races + list(sc_races.values()),
                                             key=lambda r: (r["date"], r["discipline"], r["gender"], r["name_fi"]))
            results.update(sc_res)
    used_keys = set()
    for r in [r for rs in races_by_event.values() for r in rs] + [r for e in other_events for r in e.get("races", [])]:
        key = race_results.race_key(r)
        if key and key in results and r["date"] >= results_from:
            r["res"] = key
            used_keys.add(key)
        else:
            r.pop("res", None)
    results = {k: v for k, v in results.items() if k in used_keys}
    if res_errors:
        print(f"VAROITUS: tulokset osin vanhaa dataa: {res_errors}", file=sys.stderr)
        status["results"] = {"ok": False, "error": "; ".join(f"{k}: {v}" for k, v in res_errors.items())[:300],
                             "updated": prev_status.get("results", {}).get("updated")}
    else:
        status["results"] = {"ok": True, "updated": now.isoformat(timespec="minutes")}

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
        "standings": lists,
        "athletes": ath,
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n_races = sum(len(v) for v in races_by_event.values())
    print(f"OK: {len(out_events) - len(other_events)} Ylen tapahtumaa + {len(other_events)} muuta, {n_races} kisaa, {len(broadcasts)} lähetystä → {out_path}")
    print(f"    Telkku: {'ok' if status['telkku']['ok'] else 'VANHA DATA'}, FIS: {'ok' if status['fis']['ok'] else 'VANHA DATA'}, "
          f"pisteet: {'ok' if status['standings']['ok'] else 'OSIN VANHA'} "
          f"({', '.join(f'{s["id"]} {s["done"]}/{s["total"]}' for s in lists)}), "
          f"profiilit: {len(ath)} {'ok' if status['athletes']['ok'] else 'OSIN VANHA'}, "
          f"tulokset: {len(results)} {'ok' if status['results']['ok'] else 'OSIN VANHA'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
