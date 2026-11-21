"""Kisojen top 30 -tulokset Kauden kisat -välilehdelle (vaihe 6).

Lähteet:
- FIS `results.html?sectorcode=…&raceid=…`: maailmancup, MM, Tour de Ski, SM ja yhdistetyn
  hiihto-osuus. Kisan osoite on valmiina kisarivillä (FIS iCal).
- Hiihtoliiton tapahtumasivun tulos-PDF:t: Suomen cup, joka ei ole FIS:n kalenterissa.
  PDF:t tekee EQ Timing / EQ Events, ja ne luetaan `pdftotext -layout` -komennolla (poppler-utils).

Sprintin finalisteille (sijat 1–6) haetaan lisäksi finaalin aika ja ero (vaihe 6b):
- FIS: tulossivun "Results"-PDF, finaalin sarake
- Suomen cup: EQ Eventsin live-tulospalvelu (`live.time4results.com`), finaalin maalilista

Sprinteistä näytetään vain lopputulokset (karsinnoille ei omaa listaa). Tulos haetaan uudelleen
vielä kaksi vuorokautta kisan jälkeen (korjaukset); sen jälkeen se jäädytetään edellisestä datasta.
"""
import html
import re
import shutil
import subprocess
import time
import urllib.parse
from datetime import date, datetime, timedelta

from net import fetch

TOP = 30
REFRESH_DAYS = 2              # päivää kisan jälkeen, joina tulos haetaan vielä uudelleen
SC_BACKFILL_DAYS = 30         # päivää tapahtuman jälkeen, joina puuttuvia SC-tuloksia vielä etsitään
MAX_FIS_FETCHES = 40          # yhdessä ajossa (ensimmäinen ajo kesken kauden)
FIS_DELAY = 1.0

PHASE_FIS = {"final": "Finaali", "semifinal": "Välierä", "1/4 final": "Puolivälierä",
             "quarterfinal": "Puolivälierä", "qualification": "Karsinta"}
PHASE_PDF = [("finaali", "Finaali"), ("semifinaali", "Välierä"), ("välierä", "Välierä"),
             ("erä", "Puolivälierä"), ("karsinta", "Karsinta")]

TIME_RE = r"\d{1,2}:\d\d(?::\d\d)?\.\d+"


def _text(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def display_name(fis_name: str) -> str:
    """"KLAEBO Johannes Hoesflot" → "Johannes Hoesflot Klaebo" (sama muoto kuin pistetilanteessa)."""
    words = fis_name.split()
    n = 0
    while n < len(words) and words[n].upper() == words[n] and re.search(r"[A-ZÄÖÅ]", words[n]):
        n += 1
    if n == 0 or n == len(words):
        return fis_name
    surname = " ".join("-".join(p.capitalize() for p in w.split("-")) for w in words[:n])
    return f'{" ".join(words[n:])} {surname}'


def surname(name: str) -> str:
    return name.split()[-1] if name else name


def race_key(race: dict) -> str | None:
    """Tuloksen avain: FIS-kisoille laji + raceid, SC-kisoille valmis `res`."""
    if race.get("res"):
        return race["res"]
    m = re.search(r"raceid=(\d+)", race.get("url") or "")
    return f'fis-{race.get("discipline", "CC")}-{m.group(1)}' if m else None


def is_qualification(race: dict) -> bool:
    return "karsinta" in (race.get("name_fi") or "").lower()


# --- FIS ---------------------------------------------------------------------

def parse_fis(page: str) -> dict | None:
    """FIS:n tulossivu → {"kind", "rows", "ranked"}. None, jos kisaa ei ole vielä ajettu.
    Nostaa poikkeuksen, jos sivu ei ole tulossivu (rakenne muuttunut)."""
    start = page.find('id="events-info-results"')
    if start < 0:
        raise ValueError("FIS-tulossivulta puuttuu tulostaulukko")
    kind_m = re.search(r'class="event-header__kind"[^>]*>(.*?)</div>', page, re.S)
    kind_txt = _text(kind_m.group(1)) if kind_m else ""
    body = page[start:]
    tokens = re.finditer(r'thead_slave.*?<div class="g-xs-24[^"]*">(.*?)</div>|<a class="table-row(.*?)</a>', body, re.S)
    rows: list[dict] = []
    phase = None
    team = None
    ranked = 0
    for t in tokens:
        if t.group(1) is not None:                        # sprintin vaiheotsikko: Final / Semifinal / …
            phase = PHASE_FIS.get(_text(t.group(1)).lower())
            continue
        chunk = t.group(2)
        cells = [_text(c) for c in re.findall(r'<div class="[^"]*\bg-(?:lg|xs)[^"]*"[^>]*>(.*?)</div>', chunk, re.S)]
        if len(cells) < 4:
            continue
        rank_txt, bib = cells[0], cells[1]
        if re.match(r"^\d+\s*-\s*\d+$", bib):              # viestin / parisprintin osuus
            if team is not None:
                team.setdefault("members", []).append(surname(display_name(cells[3])))
            continue
        team = None
        if not rank_txt.isdigit():
            continue                                       # DNF, DNS, DSQ
        rank = int(rank_txt)
        ranked += 1
        if rank > TOP:
            continue
        name_m = re.search(r'justify-left bold[^"]*">(.*?)</div>', chunk, re.S)
        nat = re.search(r'country__name-short">([A-Z]{3})<', chunk)
        tm = re.search(r'justify-right blue bold[^"]*">(.*?)</div>', chunk, re.S)
        diff = next((c for c in cells if re.fullmatch(r"\+\d[\d:.]*", c)), None)
        row = {"rank": rank, "name": display_name(_text(name_m.group(1))) if name_m else cells[3]}
        if nat:
            row["nat"] = nat.group(1)
        if tm and re.fullmatch(TIME_RE, _text(tm.group(1))):
            row["time"] = _text(tm.group(1))
        if diff:
            row["diff"] = diff
        if phase and phase != "Karsinta":
            row["phase"] = phase
        if re.search(r"Relay|Team", kind_txt):             # joukkuerivi: "NORWAY II" → "Norway II"
            row["name"] = " ".join(w if re.fullmatch(r"[IVX]+", w) else w.capitalize() for w in row["name"].split())
            team = row
        rows.append(row)
    if not rows:
        return None
    for r in rows:
        if r.get("members") == []:
            del r["members"]
    return {"kind": kind_txt, "rows": rows, "ranked": ranked}


def fetch_fis(url: str) -> dict | None:
    return parse_fis(fetch(url).decode("utf-8", errors="replace"))


# --- Sprintin finaaliajat ---------------------------------------------------------

def fis_results_pdf_url(page: str) -> str | None:
    """FIS-tulossivun latauslistasta "Results"-PDF:n osoite."""
    for m in re.finditer(r'data-link="([^"]+\.pdf)".*?justify-left">([^<]*)</div>', page, re.S):
        if m.group(2).strip() == "Results":
            return html.unescape(m.group(1))
    return None


def parse_fis_final_pdf(text: str) -> dict[int, dict]:
    """FIS:n sprintin tulos-PDF (pdftotext -layout) → {sija: {"time": …} | {"diff": …}} finalisteille.
    Finaalin arvo on rivin viimeinen sarake ("2:28.82(1)", "+0.13(2)"); jos finalistilta puuttuu
    finaaliaika (esim. DNF), viimeinen arvo on välierästä ja jää pois sarakkeen sijainnin perusteella."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == "Final"), None)
    if start is None:
        return {}
    found = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if re.fullmatch(r"\s*[A-Za-z/ ]+\s*", line):        # seuraava väliotsikko (Semifinals)
            break
        m = re.match(r"^\s*(\d+)\s+\d+\s", line)
        if m:
            found.append((int(m.group(1)), re.search(r"(\+?\d[\d:.]*)\((?:\d+|PF\d+)\)\s*$", line), len(line.rstrip())))
    ends = [end for _, m, end in found if m]
    if not ends:
        return {}
    col = max(ends)
    out = {}
    for rank, m, end in found:
        if m and end >= col - 3:
            v = m.group(1)
            out[rank] = {"diff": v} if v.startswith("+") else {"time": v}
    return out


def add_final_times(rows: list[dict], times: dict, key_of) -> int:
    """Lisää finalisteille aika/ero. key_of(i, row) → avain times-sanakirjaan. Palauttaa lisättyjen määrän."""
    n = 0
    for i, row in enumerate(rows):
        if row.get("phase") != "Finaali" or "time" in row or "diff" in row:
            continue
        t = times.get(key_of(i, row))
        if t:
            row.update(t)
            n += 1
    return n


def parse_live_final(page: str) -> dict[str, dict]:
    """time4results-palvelun finaalin maalilista → {kilpailunumero: {"time"} | {"diff"}}."""
    out = {}
    for m in re.finditer(r"<tr>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*>.*?</td>\s*"
                         r"<td[^>]*>(" + TIME_RE + r")</td>\s*<td[^>]*>([+\d:.]+)</td>\s*</tr>", page, re.S | re.I):
        rank, bib, tm, diff = int(m.group(1)), m.group(2), m.group(3), m.group(4)
        out[bib] = {"time": tm} if rank == 1 else {"diff": diff if diff.startswith("+") else "+" + diff}
    return out


def fetch_live_finals(event: dict, delay: float = FIS_DELAY) -> dict[str, dict[str, dict]]:
    """Suomen cupin sprinttien finaaliajat live-tulospalvelusta → {sukupuoli: {numero: aika/ero}}.
    Palvelun etusivun otsikosta tarkistetaan tapahtuman päivä ja vuosi (sama osoite voi jäädä vanhaksi)."""
    base = event["live_results"]
    root = fetch(base).decode("iso-8859-1")
    title = " ".join(_text(t) for t in re.findall(r"<title>(.*?)</title>", root, re.S | re.I)
                     + re.findall(r"<h2>(.*?)</h2>", root, re.S | re.I))
    start = date.fromisoformat(event["start"])
    if str(start.year) not in title or not re.search(rf"\b{start.day}\.", title):
        raise ValueError(f"live-tulospalvelu ei ole tämän tapahtuman ({title.strip()[:60]})")
    out: dict[str, dict[str, dict]] = {}
    for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]*Sprintti\s+erät[^<]*)<', root, re.I):
        gender = "M" if re.search(r"miehet", m.group(2), re.I) else "N" if re.search(r"naiset", m.group(2), re.I) else None
        if not gender:
            continue
        idx_url = urllib.parse.urljoin(base, m.group(1))
        time.sleep(delay)
        idx = fetch(idx_url).decode("iso-8859-1")
        fm = re.search(r"Finaali\s*</td>\s*<td[^>]*>\s*<a href=\"([^\"]+)\">\s*Maali", idx, re.I)
        if not fm:
            continue                                       # finaali ei vielä maalissa
        fin_url = urllib.parse.urljoin(idx_url, fm.group(1))
        time.sleep(delay)
        times = parse_live_final(fetch(fin_url).decode("iso-8859-1"))
        if not times:                                      # lista ladataan joskus erikseen: 6_9_1_.html
            times = parse_live_final(fetch(fin_url.replace(".html", "_.html")).decode("iso-8859-1"))
        if times:
            out[gender] = times
    return out


# --- Suomen cup: Hiihtoliiton sivu ja EQ Timing -PDF:t -------------------------

PDF_SKIP = re.compile(r"karsin|pistetilan|l[aä]ht[oö]lista|startlist|kaavio|info|ohje|kartta|reitti|testaus|erityisalue|data", re.I)
PDF_WANT = re.compile(r"tulokset|_res\b|_res[-_.]|lopputulos", re.I)


def pdf_links(page: str, base: str) -> list[tuple[str, str]]:
    """Tapahtumasivun tulos-PDF:t [(url, linkkiteksti)] sivun järjestyksessä, ilman toistoja."""
    out, seen = [], set()
    for m in re.finditer(r'<a\s[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', page, re.S | re.I):
        url = urllib.parse.urljoin(base, html.unescape(m.group(1)))
        text = _text(m.group(2))
        fname = url.rsplit("/", 1)[-1]
        if url in seen or PDF_SKIP.search(fname) or PDF_SKIP.search(text):
            continue
        if not (PDF_WANT.search(fname) or PDF_WANT.search(text)):
            continue
        seen.add(url)
        out.append((url, text))
    return out


def pdf_to_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise ValueError("ei PDF-tiedosto (rikkinäinen linkki?)")
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext puuttuu (poppler-utils)")
    res = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data, capture_output=True, timeout=60)
    if res.returncode != 0:
        raise ValueError(f"pdftotext epäonnistui: {res.stderr[:200]!r}")
    return res.stdout.decode("utf-8", errors="replace")


def _lead(line: str) -> str:
    """Rivin alun teksti ensimmäiseen isoon väliin asti."""
    return re.split(r"\s{2,}", line.strip())[0].strip()


def _pdf_title(text: str) -> tuple[str | None, str | None, str | None]:
    """(sukupuoli, kisan nimi, päivä ISO) PDF:n otsikosta, esim. "Miehet Sprintti (P)", "21.11.2026"."""
    gender = name = day = None
    head = text.split("Sija", 1)[0].split("Sij ", 1)[0]
    for line in head.splitlines():
        s = line.strip()
        m = re.match(r"^(Miehet|Naiset|Pojat|Tytöt|Sekaviesti|Seka)\b\s*(.*)$", s)
        if m and gender is None:
            gender = {"Miehet": "M", "Naiset": "N", "Pojat": "M", "Tytöt": "N"}.get(m.group(1), "Seka")
            name = m.group(2).strip()
        d = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b", s)
        if d and day is None:
            day = f"{d.group(3)}-{int(d.group(2)):02d}-{int(d.group(1)):02d}"
    km = re.search(r"^\s*(\d+(?:,\d+)?) km Sprintti\b", head, re.M)
    if name and re.match(r"(?i)sprintti", name) and km:
        name = f"{km.group(1)} km {name}"
    if name:
        name = name.lower()
    return gender, name, day


def parse_eq_pdf(text: str) -> dict:
    """EQ Timing -tulos-PDF (pdftotext -layout) → {"gender", "name", "date", "kind", "rows", "ranked"}.
    Nostaa poikkeuksen, jos tuloksia ei tunnisteta."""
    gender, name, day = _pdf_title(text)
    lines = [l for l in text.splitlines() if l.strip()]
    rows: list[dict] = []
    bibs: list[str | None] = []
    ranked = 0
    team = None
    relay = bool(re.search(r"Joukkue\s*/\s*Nimi", text))
    for i, line in enumerate(lines):
        if relay:
            mt = re.match(r"^\s*(\d+)\s+(\d+)\s{2,}(\S.*?)\s{2,}(" + TIME_RE + r")\s+(\+?[\d:.]+)\s*$", line)
            mm = re.match(r"^\s*\d+\s*-\s*\d\s+(\S.*?)\s{2,}", line)
            if mt:
                ranked += 1
                team = None
                if int(mt.group(1)) <= TOP:
                    team = {"rank": int(mt.group(1)), "name": mt.group(3).strip(), "time": mt.group(4)}
                    if mt.group(5).startswith("+"):
                        team["diff"] = mt.group(5)
                    rows.append(team)
                    bibs.append(mt.group(2))
            elif mm and team is not None:
                team.setdefault("members", []).append(surname(mm.group(1).strip()))
            continue
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d{7,8})\b(.*)$", line)
        if not m:
            continue
        ranked += 1
        rank, rest = int(m.group(1)), m.group(4)
        if rank > TOP:
            continue
        prev = lines[i - 1] if i > 0 else ""
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        row = {"rank": rank, "name": _lead(prev)}
        lead_rest = _lead(rest)
        if lead_rest and not re.match(r"^[\d:.+]", lead_rest):   # matka: seura samalla rivillä, lopussa aika ja ero
            row["club"] = lead_rest
            tail = re.search(r"(" + TIME_RE + r")\s+(\+?[\d:.]+)\s*$", rest)
            if tail:
                row["time"] = tail.group(1)
                if tail.group(2).startswith("+"):
                    row["diff"] = tail.group(2)
        else:                                                    # sprintti: seura seuraavalla rivillä
            row["club"] = _lead(nxt)
            ph = re.search(TIME_RE + r"\s+(Finaali|Semifinaali|Välierä|Erä|Karsinta)\b", rest, re.I)
            label = next((lab for key, lab in PHASE_PDF if ph and ph.group(1).lower() == key), None)
            if label and label != "Karsinta":
                row["phase"] = label
        rows.append(row)
        bibs.append(m.group(2))
    if not rows or rows[0]["rank"] != 1 or any(not r["name"] for r in rows):
        raise ValueError("PDF:stä ei tunnistettu tulosrivejä")
    kind = "relay" if relay else ("sprint" if any("phase" in r for r in rows) else "distance")
    return {"gender": gender, "name": name, "date": day, "kind": kind, "rows": rows, "ranked": ranked, "bibs": bibs}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("ä", "a").replace("ö", "o")).strip("-")


def _gender_from_text(text: str) -> str | None:
    low = text.lower()
    if re.search(r"\bmie(het|sten)\b|\bm\b", low):
        return "M"
    if re.search(r"\bnai(set|sten)\b|\bn\b", low):
        return "N"
    return None


def fetch_sc_event(event: dict, now: datetime, delay: float = FIS_DELAY) -> tuple[list[dict], dict[str, dict], list[str]]:
    """Hiihtoliiton tapahtumasivun tulos-PDF:t → (kisat, tulokset, virheet).
    Vain tapahtuman päiville osuvat PDF:t hyväksytään (sivuja käytetään uudelleen vuodesta toiseen)."""
    page_url = event["results_page"]
    page = fetch(page_url).decode("utf-8", errors="replace")
    start = date.fromisoformat(event["start"]) - timedelta(days=1)
    end = date.fromisoformat(event["end"]) + timedelta(days=1)
    races: dict[str, dict] = {}
    results: dict[str, dict] = {}
    errors: list[str] = []
    for url, text in pdf_links(page, page_url):
        try:
            time.sleep(delay)
            data = fetch(url)
            if not data.startswith(b"%PDF"):
                print(f"HUOM: rikkinäinen PDF-linkki ohitetaan: {url}")
                continue
            parsed = parse_eq_pdf(pdf_to_text(data))
        except Exception as exc:  # noqa: BLE001
            if "HTTP Error 404" in str(exc):
                print(f"HUOM: rikkinäinen PDF-linkki ohitetaan: {url}")
            else:
                errors.append(f"{url.rsplit('/', 1)[-1]}: {exc}"[:160])
            continue
        if not parsed["date"] or not (start <= date.fromisoformat(parsed["date"]) <= end):
            continue                                       # edellisen vuoden PDF samalla sivulla
        gender = parsed["gender"] or _gender_from_text(text) or "?"
        name = parsed["name"] or text
        if parsed["kind"] == "relay" and "viesti" not in name:
            name = re.sub(r"\s*(\([pvk/]+\))?$", lambda m: " viesti" + (f" {m.group(1)}" if m.group(1) else ""), name, count=1)
        key = f'sc-{event["id"]}-{parsed["date"]}-{gender}-{_slug(name)}'
        if key in races and "korjattu" not in url.lower():
            continue                                       # sama kisa kahdesti: korjattu versio voittaa
        races[key] = {"date": parsed["date"], "discipline": "CC", "gender": gender, "name_fi": name,
                      "url": url, "res": key}
        results[key] = {"kind": parsed["kind"], "rows": parsed["rows"], "ranked": parsed["ranked"],
                        "url": url, "source": "Hiihtoliitto (PDF)", "updated": now.isoformat(timespec="minutes"),
                        "_bibs": parsed["bibs"]}
    sprints = [k for k, v in results.items() if v["kind"] == "sprint"]
    if sprints and event.get("live_results"):
        try:
            finals = fetch_live_finals(event, delay)
        except Exception as exc:  # noqa: BLE001 – finaaliajat ovat lisätietoa, lista näytetään ilmankin
            print(f"HUOM: finaaliajat puuttuvat ({event['id']}): {exc}")
            finals = {}
        for k in sprints:
            times, bibs = finals.get(races[k]["gender"], {}), results[k]["_bibs"]
            add_final_times(results[k]["rows"], times, lambda i, row: bibs[i])
    for v in results.values():
        v.pop("_bibs", None)
    out = sorted(races.values(), key=lambda r: (r["date"], r["gender"], r["name_fi"]))
    return out, results, errors


# --- Kokoaminen -------------------------------------------------------------------

def due(race: dict, prev: dict, today: date) -> bool:
    """Haetaanko FIS-kisan tulos tässä ajossa?"""
    key = race_key(race)
    if not key or is_qualification(race) or not race.get("url"):
        return False
    d = date.fromisoformat(race["date"])
    if d > today:
        return False
    return key not in prev or (today - d).days <= REFRESH_DAYS


def fetch_fis_results(races: list[dict], prev: dict, now: datetime,
                      delay: float = FIS_DELAY) -> tuple[dict[str, dict], dict[str, str]]:
    """FIS-kisojen tulokset. Palauttaa (tulokset avaimittain, virheet). Edelliset tulokset säilyvät."""
    today = now.date()
    out = {k: v for k, v in prev.items() if k.startswith("fis-")}
    errors: dict[str, str] = {}
    todo = sorted((r for r in races if due(r, prev, today)), key=lambda r: r["date"], reverse=True)
    for r in todo[:MAX_FIS_FETCHES]:
        key = race_key(r)
        try:
            page = fetch(r["url"]).decode("utf-8", errors="replace")
            parsed = parse_fis(page)
        except Exception as exc:  # noqa: BLE001
            errors[key] = str(exc)[:160]
            continue
        finally:
            time.sleep(delay)
        if parsed is None:
            continue                                       # ei vielä tuloksia
        kind = ("relay" if re.search(r"Relay|Team", parsed["kind"]) and any("members" in x for x in parsed["rows"])
                else "sprint" if any("phase" in x for x in parsed["rows"]) else "distance")
        if kind == "sprint" and any(x.get("phase") == "Finaali" and "time" not in x for x in parsed["rows"]):
            try:                                           # finaaliajat tulos-PDF:stä
                pdf = fis_results_pdf_url(page)
                if pdf:
                    times = parse_fis_final_pdf(pdf_to_text(fetch(pdf)))
                    add_final_times(parsed["rows"], times, lambda i, row: row["rank"])
            except Exception as exc:  # noqa: BLE001 – lisätietoa, lista näytetään ilmankin
                print(f"HUOM: finaaliajat puuttuvat ({key}): {exc}")
            finally:
                time.sleep(delay)
        out[key] = {"kind": kind, "rows": parsed["rows"], "ranked": parsed["ranked"], "url": r["url"],
                    "source": "FIS", "updated": now.isoformat(timespec="minutes")}
    return out, errors


def missing_finals(res: dict) -> bool:
    return res.get("kind") == "sprint" and any(
        r.get("phase") == "Finaali" and "time" not in r and "diff" not in r for r in res.get("rows", []))


def sc_due(event: dict, prev_races: list[dict], today: date, prev_results: dict | None = None) -> bool:
    if event.get("type") != "SC" or not event.get("results_page"):
        return False
    start, end = date.fromisoformat(event["start"]), date.fromisoformat(event["end"])
    if today < start:
        return False
    if (today - end).days <= REFRESH_DAYS:
        return True
    if (today - end).days > SC_BACKFILL_DAYS:
        return False
    if not prev_races:
        return True
    return bool(event.get("live_results")) and any(                  # finaaliajat puuttuvat vielä
        missing_finals((prev_results or {}).get(r.get("res"), {})) for r in prev_races)
