"""Maailmancupin pistetilanne (kokonaiskilpailu).

- Hiihto ja yhdistetty: FIS:n viralliset cup standings -sivut (HTML).
- Ampumahiihto: englanninkielisen Wikipedian kausisivu (IBU:n rajapinta vaatii tunnistautumisen).
  Wikipediassa on vain kärkikymmenikkö.
"""
import html
import json
import re
import urllib.parse

from net import fetch

FIS_SECTORS = {"hiihto": ("cross-country", "CC"), "yhdistetty": ("nordic-combined", "NK")}
GENDERS = [("M", "M"), ("W", "N")]                 # FIS-koodi → sivun merkintä
KEEP_TOP = 10
HOME_NATION = "FIN"


# --- FIS --------------------------------------------------------------------

def fis_url(cfg: dict, topic: str, gender: str) -> str:
    path, sector = FIS_SECTORS[topic]
    params = {"sectorcode": sector, "seasoncode": cfg["season"], "cupcode": "WC",
              "disciplinecode": "ALL", "gendercode": gender, "nationcode": ""}
    return cfg["fis_base"].format(path=path) + "?" + urllib.parse.urlencode(params)


def _selected(page: str, select_id: str) -> str | None:
    m = re.search(rf'<select[^>]*id="{select_id}".*?</select>', page, re.S)
    if not m:
        return None
    opt = re.search(r'<option value="([^"]*)" selected', m.group(0))
    return opt.group(1) if opt else None


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def display_name(fis_name: str) -> str:
    """"KLAEBO Johannes Hoesflot" → "Johannes Hoesflot Klaebo" (FIS kirjoittaa sukunimen versaalilla)."""
    words = fis_name.split()
    n = 0
    while n < len(words) and words[n].upper() == words[n] and re.search(r"[A-ZÀ-Þ]", words[n]):
        n += 1
    if n == 0 or n == len(words):
        return fis_name
    surname = " ".join("-".join(p.capitalize() for p in w.split("-")) for w in words[:n])
    return f'{" ".join(words[n:])} {surname}'


def parse_fis(page: str, season: str) -> dict | None:
    """Palauttaa {"done", "total", "rows"} tai None, jos sivu ei näytä pyydetyn kauden maailmancupia.
    (Ennen kauden ensimmäistä MC-kisaa FIS näyttää hiljaa jonkin toisen cupin.)"""
    if _selected(page, "cupcode") != "WC" or _selected(page, "seasoncode") != season:
        return None
    note = re.search(r'class="note note_text">([^<]*)<', page)
    done = total = 0
    if note:
        m = re.search(r"\((\d+)/(\d+)\)\s*$", html.unescape(note.group(1)).strip())
        if m:
            done, total = int(m.group(1)), int(m.group(2))
    rows = []
    for chunk in page.split('<a class="table-row')[1:]:
        href = re.search(r'href="([^"]*competitorid=\d+[^"]*)"', chunk)
        name = re.search(r'<div class="[^"]*justify-left bold[^"]*">(.*?)</div>', chunk, re.S)
        nation = re.search(r'country__name-short">([A-Z]{3})<', chunk)
        # ensimmäinen lihavoitu sijoitus–pisteet-pari on kokonaiskilpailu (ALL)
        rp = re.search(r'justify-right bold">\s*(\d+)\s*</div>.*?justify-right bold">\s*([\d\'’]+)\s*</div>', chunk, re.S)
        if not (name and nation and rp):
            continue
        rows.append({
            "rank": int(rp.group(1)),
            "name": display_name(_text(name.group(1))),
            "nation": nation.group(1),
            "points": int(re.sub(r"\D", "", rp.group(2))),
            "url": html.unescape(href.group(1)) if href else None,
        })
    if done and not rows:
        raise RuntimeError("FIS-pistetaulukosta ei löytynyt rivejä – sivun rakenne muuttunut?")
    return {"done": done, "total": total, "rows": rows}


# --- Wikipedia (ampumahiihto) ---------------------------------------------------

def wiki_title(season: str) -> str:
    """"2027" → "2026–27 Biathlon World Cup"."""
    y = int(season)
    return f"{y - 1}–{str(y)[2:]} Biathlon World Cup"


def wiki_api_url(cfg: dict) -> str:
    params = {"action": "parse", "page": wiki_title(cfg["season"]), "prop": "wikitext",
              "format": "json", "formatversion": "2"}
    return cfg["wikipedia_api"] + "?" + urllib.parse.urlencode(params)


def _wiki_link(cell: str) -> tuple[str, str] | None:
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", re.sub(r"\[\[(?:Image|File):[^\]]*\]\]", "", cell))
    if not m:
        return None
    return m.group(2) or m.group(1), m.group(1)


def parse_wiki_table(table: str) -> dict:
    head = re.search(r"standings after (\d+)(?: of (\d+))? events", table)
    done = int(head.group(1)) if head else 0
    total = int(head.group(2)) if head and head.group(2) else done
    rows = []
    for line in table.splitlines():
        if not line.startswith("|") or "||" not in line:
            continue
        cells = line.lstrip("|").split("||")
        if len(cells) < 3:
            continue
        rank = re.search(r"(\d+)\s*$", cells[0])
        link = _wiki_link(cells[1])
        flag = re.search(r"\{\{flagicon\|([A-Z]{3})\}\}", cells[1])
        pts = re.search(r"(\d+)", cells[2].replace("'''", ""))
        if not (rank and link and flag and pts):
            continue
        name, article = link
        rows.append({"rank": int(rank.group(1)), "name": name, "nation": flag.group(1),
                     "points": int(pts.group(1)),
                     "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(article.replace(" ", "_"))})
    return {"done": done if rows else 0, "total": total, "rows": rows}


def parse_wiki(wikitext: str) -> dict[str, dict]:
    """Palauttaa {"M": {...}, "N": {...}} sivun Men/Women-osioiden Overall-taulukoista."""
    out = {}
    parts = re.split(r"^==\s*(Men|Women|Mixed[^=]*)\s*==\s*$", wikitext, flags=re.M)
    for label, body in zip(parts[1::2], parts[2::2]):
        g = {"Men": "M", "Women": "N"}.get(label.strip())
        if not g:
            continue
        m = re.search(r"^====\s*(?:\[\[[^\]|]*\|)?Overall(?:\]\])?\s*====\s*$(.*?)^\|\}", body, re.M | re.S)
        if m:
            out[g] = parse_wiki_table(m.group(1))
    return out


# --- Kokoaminen ------------------------------------------------------------------

def trim(rows: list[dict]) -> list[dict]:
    """Kärkikymmenikkö + paras suomalainen, jos hän ei ole kärjessä."""
    top = rows[:KEEP_TOP]
    if not any(r["nation"] == HOME_NATION for r in top):
        fin = next((r for r in rows if r["nation"] == HOME_NATION), None)
        if fin:
            top = top + [fin]
    return top


def make_list(topic: str, gender: str, season: str, source: str, url: str, parsed: dict | None) -> dict:
    parsed = parsed or {"done": 0, "total": 0, "rows": []}
    return {"id": f"{topic}-{gender}", "topic": topic, "gender": gender, "season": season,
            "source": source, "url": url, "done": parsed["done"], "total": parsed["total"],
            "rows": trim(parsed["rows"])}


def fetch_standings(cfg: dict) -> tuple[list[dict], dict[str, str]]:
    """Palauttaa (listat, virheet listan id:n mukaan). Epäonnistunut lista puuttuu tuloksesta."""
    lists, errors = [], {}
    season = cfg["season"]
    for topic in FIS_SECTORS:
        for fis_g, g in GENDERS:
            url = fis_url(cfg, topic, fis_g)
            try:
                page = fetch(url).decode("utf-8", errors="replace")
                lists.append(make_list(topic, g, season, "FIS", url, parse_fis(page, season)))
            except Exception as exc:  # noqa: BLE001
                errors[f"{topic}-{g}"] = str(exc)[:200]
    page_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(wiki_title(season).replace(" ", "_"))
    try:
        data = json.loads(fetch(wiki_api_url(cfg)))
        if "error" in data:
            raise RuntimeError(data["error"].get("info", "Wikipedia-virhe"))
        parsed = parse_wiki(data["parse"]["wikitext"])
        for g in ("M", "N"):
            if g not in parsed:
                raise RuntimeError(f"Wikipedian Overall-taulukko puuttuu ({g})")
            lists.append(make_list("ampumahiihto", g, season, "Wikipedia", page_url, parsed[g]))
    except Exception as exc:  # noqa: BLE001
        for g in ("M", "N"):
            errors[f"ampumahiihto-{g}"] = str(exc)[:200]
    return lists, errors
