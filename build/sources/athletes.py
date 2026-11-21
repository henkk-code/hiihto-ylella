"""Maastohiihtäjien profiilit Maailmancup-välilehdelle (vaihe 5, taso B).

Kenelle: hiihdon pistetilanteen tallennetut rivit (kärkikymmenikkö + paras suomalainen, M ja N).
Tunniste on FIS:n competitorid pistetilanteen linkistä, joten nimiä ei tarvitse sovittaa.

Per hiihtäjä:
- FIS-urheilijasivu, kauden MC-tulokset (`type=result&categorycode=WC`) + seura ja syntymäaika
- FIS-urheilijasivu, MC-palkintosijat kausittain (`type=podiums`) → uran voitot ja palkintosijat
- FIS-urheilijasivu, olympia- ja MM-tulokset kaikilta kausilta (OWG, WSC) → mitalit (myös viestit ja parisprintit)
Kaikille kerralla:
- Wikidata SPARQL (P2773 = FIS competitorid) → syntymäpaikka ja suomenkielinen Wikipedia-artikkeli
- Wikipedia REST page/summary → ingressi (vain fi; jos artikkelia ei ole, ingressiä ei näytetä)

Päivitystahti: tulokset ja ura haetaan uudelleen, kun hiihtäjän MC-pisteet muuttuvat tai tieto
on yli viikon vanha. Mitalit haetaan viikoittain ja MM-kisojen aikana joka ajossa.
Epäonnistunut haku → edellinen profiili säilyy.
"""
import html
import json
import re
import time
import urllib.parse
from datetime import date, datetime, timedelta

from net import fetch

FIS_BIO = "https://www.fis-ski.com/DB/general/athlete-biography.html"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKI_SUMMARY = "https://fi.wikipedia.org/api/rest_v1/page/summary/"
REFRESH_AFTER = timedelta(days=7)
FIS_DELAY = 1.0                     # sekuntia FIS-hakujen välissä

RACE_FI = [                          # FIS:n lajinimi → suomi (jos kalenterista ei löydy kisan nimeä)
    ("Heat Mass Start", "yhteislähtö (erät)"),
    ("Team Sprint", "parisprintti"),
    ("Sprint Final", "sprintti"),
    ("Sprint Qualification", "sprintti"),
    ("Sprint", "sprintti"),
    ("Interval Start", "väliaikalähtö"),
    ("Mass Start", "yhteislähtö"),
    ("Skiathlon", "yhdistelmähiihto"),
    ("Pursuit", "takaa-ajo"),
    ("Team", "viesti"),
    ("Relay", "viesti"),
]


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def competitor_id(url: str | None) -> str | None:
    m = re.search(r"competitorid=(\d+)", url or "")
    return m.group(1) if m else None


def bio_url(cid: str, kind: str, category: str = "", season: str = "") -> str:
    params = {"sectorcode": "CC", "competitorid": cid, "type": kind}
    if category:
        params["categorycode"] = category
    if kind == "result":
        params["seasoncode"] = season          # tyhjä = kaikki kaudet
        params["limit"] = "1000"
    return FIS_BIO + "?" + urllib.parse.urlencode(params)


def profile_url(cid: str) -> str:
    return f"{FIS_BIO}?sectorcode=CC&competitorid={cid}&type=result"


# --- FIS-jäsentimet -------------------------------------------------------------

def parse_bio(page: str) -> dict:
    """Seura ja syntymäaika urheilijasivun yläosasta."""
    out = {}
    club = re.search(r'class="athlete-profile__team[^"]*">(.*?)</div>', page, re.S)
    if club and _text(club.group(1)):
        name = _text(club.group(1))
        out["club"] = name.title() if name.isupper() else name      # "GRUPPO SPORTIVO …" → "Gruppo Sportivo …"
    bd = re.search(r'id="Birthdate">.*?profile-info__value[^"]*">\s*(\d\d)-(\d\d)-(\d{4})\s*<', page, re.S)
    if bd:
        out["birthdate"] = f"{bd.group(3)}-{bd.group(2)}-{bd.group(1)}"
    return out


def parse_results(page: str) -> list[dict]:
    """Urheilijasivun tuloslista → [{raceid, date, place, race, category, rank}], uusin ensin.
    rank on int tai merkkijono (DNF, DNS, DSQ …)."""
    if 'class="athlete-profile' not in page:
        raise RuntimeError("FIS-urheilijasivun rakenne muuttunut (athlete-profile puuttuu)")
    out, seen = [], set()
    for chunk in page.split('<a class="table-row')[1:]:
        rid = re.search(r"raceid=(\d+)", chunk)
        d = re.search(r'justify-left">\s*(\d\d)-(\d\d)-(\d{4})\s*</div>', chunk)
        place = re.search(r'justify-left hidden-sm-down">(.*?)</div>', chunk, re.S)
        cells = re.findall(r'<div class="g-md-\d+ g-lg-\d+ justify-left hidden-sm-down">(.*?)</div>', chunk, re.S)
        rank = re.search(r'<div class="g-xs-24 g-sm g-md g-lg justify-right">(.*?)</div>', chunk, re.S)
        if not (rid and d and place and rank) or rid.group(1) in seen:
            continue
        seen.add(rid.group(1))
        r = _text(rank.group(1))
        m = re.match(r"(\d+)", r)
        out.append({
            "raceid": rid.group(1),
            "date": f"{d.group(3)}-{d.group(2)}-{d.group(1)}",
            "place": _text(place.group(1)),
            "category": _text(cells[0]) if cells else "",
            "race": _text(cells[1]) if len(cells) > 1 else "",
            "rank": int(m.group(1)) if m else (r.split()[0] if r else ""),
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def parse_podiums(page: str) -> dict:
    """MC-palkintosijataulukko (henkilökohtaiset, kausittain) → uran summat."""
    body = page.split('id="podiums-body"', 1)
    if len(body) < 2:
        raise RuntimeError("FIS-palkintosijataulukko puuttuu – sivun rakenne muuttunut?")
    rows = re.findall(r'bold">\s*(\d{4})\s*</div>\s*<div[^>]*>\s*(\d+)\s*</div>\s*'
                      r'<div[^>]*>\s*(\d+)\s*</div>\s*<div[^>]*>\s*(\d+)\s*</div>', body[1])
    first = sum(int(r[1]) for r in rows)
    podiums = sum(int(r[1]) + int(r[2]) + int(r[3]) for r in rows)
    return {"wins": first, "podiums": podiums}


def count_medals(results: list[dict]) -> dict:
    """Sijat 1–3 → {"g", "s", "b"}. Viestit ja parisprintit lasketaan, kuten mitalitilastoissa yleensä."""
    m = {"g": 0, "s": 0, "b": 0}
    for r in results:
        if r["rank"] in (1, 2, 3):
            m["gsb"[r["rank"] - 1]] += 1
    return m


def race_label(r: dict, race_names: dict[str, str]) -> str:
    name = race_names.get(r["raceid"])
    if name:
        return re.sub(r"sprintin (finaalit|karsinta)", "sprintti", name)
    out = r["race"]
    for en, fi in RACE_FI:
        if en in out:
            return fi
    return out


# --- Wikidata ja Wikipedia ------------------------------------------------------

def wikidata_query(ids: list[str]) -> str:
    values = " ".join(f'"{i}"' for i in ids)
    return ("SELECT ?fis ?fiwiki ?birthplaceLabel WHERE { VALUES ?fis { " + values + " } "
            "?item wdt:P2773 ?fis. OPTIONAL { ?item wdt:P19 ?birthplace } "
            "OPTIONAL { ?fiwiki schema:about ?item; schema:isPartOf <https://fi.wikipedia.org/> } "
            'SERVICE wikibase:label { bd:serviceParam wikibase:language "fi,en". } }')


def parse_wikidata(data: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for b in data.get("results", {}).get("bindings", []):
        cid = b["fis"]["value"]
        cur = out.setdefault(cid, {})
        if "fiwiki" in b and "wiki_url" not in cur:
            cur["wiki_url"] = b["fiwiki"]["value"]
        if "birthplaceLabel" in b and "birthplace" not in cur:
            label = b["birthplaceLabel"]["value"]
            if not re.fullmatch(r"Q\d+", label):          # nimetön kohde → Q-tunniste, ei näytetä
                cur["birthplace"] = label
    return out


def fetch_wikidata(ids: list[str]) -> dict[str, dict]:
    url = WIKIDATA_SPARQL + "?" + urllib.parse.urlencode({"query": wikidata_query(ids), "format": "json"})
    return parse_wikidata(json.loads(fetch(url)))


EXTRACT_MAX = 320                    # merkkiä; ingressi lyhennetään kokonaisiin virkkeisiin


def shorten(text: str, limit: int = EXTRACT_MAX) -> str:
    if len(text) <= limit:
        return text
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s+[A-ZÅÄÖ])", text) if m.end() <= limit]
    return text[:ends[-1]] if ends else text[:limit].rsplit(" ", 1)[0] + " …"


def parse_summary(data: dict) -> str | None:
    if data.get("type") not in (None, "standard"):          # täsmennyssivu tms.
        return None
    text = (data.get("extract") or "").strip()
    return shorten(text) if text else None


def fetch_summary(wiki_url: str) -> str | None:
    title = wiki_url.rsplit("/wiki/", 1)[-1]
    return parse_summary(json.loads(fetch(WIKI_SUMMARY + title)))


# --- Kokoaminen -------------------------------------------------------------------

def targets(lists: list[dict]) -> list[dict]:
    """Hiihdon pistetilanteiden rivit, joille tehdään profiili."""
    out, seen = [], set()
    for s in lists:
        if s.get("topic") != "hiihto":
            continue
        for r in s.get("rows", []):
            cid = competitor_id(r.get("url"))
            if cid and cid not in seen:
                seen.add(cid)
                out.append({"id": cid, "points": r["points"], "list": s["id"]})
    return out


def champs_active(events: list[dict], today: date) -> bool:
    """MM- tai olympiakisat käynnissä (± 1 pv) → mitalit päivitetään joka ajossa."""
    for e in events:
        if e.get("type") in ("MM", "OL"):
            if date.fromisoformat(e["start"]) - timedelta(days=1) <= today <= date.fromisoformat(e["end"]) + timedelta(days=1):
                return True
    return False


def _stale(stamp: str | None, now: datetime) -> bool:
    if not stamp:
        return True
    try:
        return now - datetime.fromisoformat(stamp) > REFRESH_AFTER
    except ValueError:
        return True


def fetch_profiles(lists: list[dict], prev: dict[str, dict], season: str, race_names: dict[str, str],
                   now: datetime, champs: bool, delay: float = FIS_DELAY) -> tuple[dict[str, dict], dict[str, str]]:
    """Palauttaa (profiilit FIS-id:n mukaan, virheet). Hiihtäjät, jotka putoavat listalta, jäävät pois."""
    stamp = now.isoformat(timespec="minutes")
    profiles: dict[str, dict] = {}
    errors: dict[str, str] = {}
    fresh: list[str] = []                                   # tulokset päivitetty tässä ajossa
    first_fetch = True

    def get(url: str) -> str:
        nonlocal first_fetch
        if not first_fetch:
            time.sleep(delay)
        first_fetch = False
        return fetch(url).decode("utf-8", errors="replace")

    for t in targets(lists):
        cid = t["id"]
        old = prev.get(cid) or {}
        p = dict(old, id=cid, fis_url=profile_url(cid))
        need_core = (old.get("season_code") != season or old.get("points") != t["points"]
                     or _stale(old.get("updated"), now))
        need_medals = champs or _stale(old.get("medals_updated"), now)
        try:
            if need_core:
                page = get(bio_url(cid, "result", "WC", season))
                results = parse_results(page)
                p.update(parse_bio(page))
                p["season"] = [{"date": r["date"], "place": r["place"], "race": race_label(r, race_names),
                                "rank": r["rank"],
                                "url": f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={r['raceid']}"}
                               for r in results]
                p["career"] = parse_podiums(get(bio_url(cid, "podiums")))
                p["points"], p["season_code"], p["updated"] = t["points"], season, stamp
                fresh.append(cid)
            if need_medals:
                p["medals"] = {
                    "ol": count_medals(parse_results(get(bio_url(cid, "result", "OWG")))),
                    "mm": count_medals(parse_results(get(bio_url(cid, "result", "WSC")))),
                }
                p["medals_updated"] = stamp
        except Exception as exc:  # noqa: BLE001
            errors[cid] = str(exc)[:200]
            if not old:
                continue                                    # ei edellistä profiilia → ei profiilia
            p = dict(old, id=cid, fis_url=profile_url(cid))
        profiles[cid] = p

    # Wikidata + Wikipedia vain, jos jonkun tulokset päivittyivät (tai tieto puuttuu kokonaan)
    wiki_needed = [cid for cid, p in profiles.items() if cid in fresh or "wiki_checked" not in p]
    if wiki_needed:
        try:
            wd = fetch_wikidata(wiki_needed)
            for cid in wiki_needed:
                p = profiles[cid]
                info = wd.get(cid, {})
                p["birthplace"] = info.get("birthplace")
                p["wiki_url"] = info.get("wiki_url")
                p["extract"] = None
                if p["wiki_url"]:
                    try:
                        p["extract"] = fetch_summary(p["wiki_url"])
                    except Exception as exc:  # noqa: BLE001
                        errors[f"wikipedia-{cid}"] = str(exc)[:200]
                p["wiki_checked"] = stamp
        except Exception as exc:  # noqa: BLE001
            errors["wikidata"] = str(exc)[:200]
    for p in profiles.values():
        for k in ("birthplace", "wiki_url", "extract"):
            if p.get(k) is None:
                p.pop(k, None)
    return profiles, errors
