"""Telkku.comin (Iltalehti) TV-opasrajapinta → ohjelmalista valituille kanaville."""
import json
import urllib.parse
from datetime import datetime, timedelta

from net import fetch


def offering_url(cfg: dict, start: datetime, end: datetime) -> str:
    q = urllib.parse.urlencode({"startTime": start.isoformat(timespec="seconds"),
                                "endTime": end.isoformat(timespec="seconds")})
    return f'{cfg["base"]}/channel-groups/{cfg["group"]}/offering?{q}'


def parse_offering(payload: dict, channel_ids: set[str]) -> tuple[list[dict], int]:
    """Palauttaa (valittujen kanavien ohjelmat, kaikkien ohjelmien määrä)."""
    programs, total = [], 0
    for ch in payload.get("response") or []:
        slots = ch.get("programs") or {}
        items = [p for slot in slots.values() if isinstance(slot, list) for p in slot]
        total += len(items)
        if str(ch.get("channelId")) not in channel_ids:
            continue
        for p in items:
            p = dict(p)
            p["channelId"] = str(ch.get("channelId"))
            programs.append(p)
    return programs, total


def fetch_programs(cfg: dict, today_start: datetime, channel_ids: set[str] | None = None) -> tuple[list[dict], int]:
    """Hakee päivä kerrallaan days_back…days_ahead. today_start = paikallinen keskiyö (aware).
    Vastauksessa on koko kanavaryhmä, joten kanavien lisääminen ei lisää hakuja."""
    channel_ids = channel_ids or set(cfg["channels"].keys())
    by_id: dict[str, dict] = {}
    total = 0
    for offset in range(-cfg["days_back"], cfg["days_ahead"] + 1):
        start = today_start + timedelta(days=offset)
        end = start + timedelta(days=1)
        payload = json.loads(fetch(offering_url(cfg, start, end)))
        programs, n = parse_offering(payload, channel_ids)
        total += n
        for p in programs:
            by_id[f'{p["channelId"]}:{p.get("id") or p.get("startTime")}'] = p
    return list(by_id.values()), total
