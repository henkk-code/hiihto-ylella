"""Urheilusivun lähetykset: kaikki suorat urheilulähetykset ilmaiskanavilta.

Säännöt ovat tiedostossa config/sports.json (SUUNNITELMA-URHEILU.md §5). Lähde on sama
Telkku-haku kuin hiihtosivulla, joten Telkkuun ei tehdä yhtään lisähakua.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

F = re.IGNORECASE
# "Snooker : UK Championship, 28.11.2026 21:00." → häntä pois
DATE_TAIL = re.compile(r"[,\s]+\d{1,2}\.\d{1,2}\.\d{4}(\s+\d{1,2}[:.]\d{2})?\.?\s*$")
# Ottelu "A - B" vain välilyönnein, koska joukkueiden nimissä on yhdysmerkkejä (Kiekko-Espoo).
MATCH = re.compile(r"^\s*(\S.*?\S)\s+[-–]\s+(\S.*?\S)\s*$")
MERGE_GAP = timedelta(minutes=5)


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, F) for p in patterns]


def _utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class SportRules:
    def __init__(self, cfg: dict):
        self.exclude = _compile(cfg.get("exclude", []))
        self.short_exclude = _compile(cfg.get("short_exclude", []))
        self.short_minutes = cfg.get("short_minutes", 60)
        self.strip = _compile(cfg.get("strip", []))
        self.generic = [{"re": re.compile(g["match"], F), "competition": g["competition"],
                         "desc_match": g.get("desc_match", False)} for g in cfg.get("generic_titles", [])]
        self.aliases = [(re.compile(a["match"], F), a["label"]) for a in cfg.get("competition_aliases", [])]
        self.sports = [{"id": s["id"], "include": _compile(s["include"])} for s in cfg["sports"]]
        self.fallback = cfg["sports"][-1]["id"]

    def skip(self, title: str, minutes: int) -> bool:
        if any(p.search(title) for p in self.exclude):
            return True
        return minutes < self.short_minutes and any(p.search(title) for p in self.short_exclude)

    def sport(self, text: str) -> str:
        for s in self.sports:
            if any(p.search(text) for p in s["include"]):
                return s["id"]
        return self.fallback

    def alias(self, prefix: str) -> str:
        for rx, label in self.aliases:
            if rx.search(prefix):
                return label
        return prefix

    def parse(self, title: str, desc: str) -> dict:
        """→ {competition, title, generic}. Kuvauksen päivämääriä ei käytetä (ne voivat olla vanhoja)."""
        t = title
        for rx in self.strip:
            t = rx.sub("", t).strip()
        t = DATE_TAIL.sub("", t).strip().rstrip(".").strip()
        for g in self.generic:
            if g["re"].search(t):
                name = match_from_description(desc) if g["desc_match"] else None
                return {"competition": g["competition"], "title": name or g["competition"], "generic": True}
        competition, name = "", t
        if ":" in t:
            prefix, rest = (s.strip() for s in t.split(":", 1))
            if prefix and rest:
                competition, name = self.alias(prefix), rest
        return {"competition": competition, "title": dash(name), "generic": False}


def dash(text: str) -> str:
    m = MATCH.match(text)
    return f"{m.group(1)} – {m.group(2)}" if m else text


def match_from_description(desc: str) -> str | None:
    """'NHL: Calgary Flames - Chicago Blackhawks. Koe NHL suorana …' → 'Calgary Flames – Chicago Blackhawks'."""
    first = re.split(r"(?<=\w)\.\s", desc or "", maxsplit=1)[0]
    first = re.sub(r"^[^:]{1,20}:\s*", "", first).split(",")[0]
    m = MATCH.match(first)
    return f"{m.group(1)} – {m.group(2)}" if m else None


def build_broadcasts(programs: list[dict], channels: dict, rules: SportRules, tz: ZoneInfo,
                     ski_classifier=None, ski_channels: set[str] = frozenset()) -> list[dict]:
    rows = []
    for p in programs:
        ch_id = str(p.get("channelId"))
        if ch_id not in channels or p.get("format") != "SPORT" or p.get("broadcastType") != "live":
            continue
        title = (p.get("programName") or "").strip()
        start, end = _utc(p["startTime"]), _utc(p["endTime"])
        if not title or rules.skip(title, int((end - start).total_seconds() // 60)):
            continue
        info = rules.parse(title, (p.get("description") or "").strip())
        ch = channels[ch_id]
        row = {
            "id": f'telkku-{ch_id}-{p.get("id") or p["startTime"]}',
            "sport": rules.sport(f'{title} {info["competition"]}'),
            "competition": info["competition"],
            "title": info["title"],
            "channel": ch["name"],
            "channel_id": ch_id,
            "watch": ch.get("watch"),
            "live_url": ch.get("live_url"),
            "start": start.astimezone(tz).isoformat(timespec="minutes"),
            "end": end.astimezone(tz).isoformat(timespec="minutes"),
            "_generic": info["generic"],
        }
        if ski_classifier and ch_id in ski_channels and ski_classifier.classify(title):
            row["ski"] = True
        also = ch.get("also_on")                         # Star Channelin NHL näkyy myös Disney+:ssa
        if also and info["competition"] == also.get("competition", info["competition"]):
            row.update(also_on=also["label"], watch=also["label"], live_url=also["url"])
        rows.append(row)

    # Geneerinen jatko-ohjelma ("Liiga") saman kanavan saman lajin lähetyksen perässä → yksi lähetys.
    rows.sort(key=lambda r: (r["channel_id"], r["start"]))
    out: list[dict] = []
    for r in rows:
        prev = out[-1] if out else None
        if (r["_generic"] and prev and prev["channel_id"] == r["channel_id"] and prev["sport"] == r["sport"]
                and datetime.fromisoformat(prev["end"]) + MERGE_GAP >= datetime.fromisoformat(r["start"])
                and prev["start"] <= r["start"]):
            prev["end"] = max(prev["end"], r["end"])
            continue
        out.append(r)
    for r in out:
        r.pop("_generic")
        for k in ("competition", "watch", "live_url"):
            if not r[k]:
                r.pop(k)
    out.sort(key=lambda r: (r["start"], r["channel"]))
    return out


def disney_games(dp: dict, broadcasts: list[dict], tz: ZoneInfo, now: datetime) -> list[dict]:
    """Käsin ylläpidetyt Disney+-ottelut (data/disneyplus.json). Menneet ja Star Channelin kanssa
    päällekkäiset (sama sarja, alku ±30 min) jätetään pois. Virheellinen rivi ohitetaan varoituksella."""
    star = [datetime.fromisoformat(b["start"]) for b in broadcasts if b.get("also_on") == "Disney+"]
    out = []
    for i, g in enumerate(dp.get("games", [])):
        try:
            start = datetime.fromisoformat(g["start"]).replace(tzinfo=tz)
            end = start + timedelta(minutes=int(g.get("duration_min", 180)))
            title = g["title"].strip()
        except (KeyError, TypeError, ValueError) as exc:
            print(f"VAROITUS: data/disneyplus.json rivi {i + 1} ohitettu: {exc}")
            continue
        if end < now or any(abs(start - s) <= timedelta(minutes=30) for s in star):
            continue
        out.append({
            "id": f"disneyplus-{start:%Y%m%d%H%M}-{i}",
            "sport": g.get("sport", "jaakiekko"),
            "competition": g.get("competition", ""),
            "title": dash(title),
            "channel": "Disney+",
            "watch": "Disney+",
            "live_url": dp.get("url"),
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
        })
    out.sort(key=lambda r: r["start"])
    return out


def page_data(cfg: dict, broadcasts: list[dict], status_telkku: dict, now: datetime, horizon_days: int,
              disney: dict | None = None) -> dict:
    order = cfg.get("display_order", [])
    return {
        "generated": now.isoformat(timespec="minutes"),
        "status": {"telkku": status_telkku},
        "horizon_days": horizon_days,
        "sports": [{"id": s["id"], "label": s["label"], "emoji": s["emoji"]}
                   for s in sorted(cfg["sports"], key=lambda s: order.index(s["id"]) if s["id"] in order else 99)],
        "broadcasts": broadcasts,
        "disneyplus": disney or {},
    }
