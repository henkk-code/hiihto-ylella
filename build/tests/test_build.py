"""Testit: python3 -m unittest discover -s build/tests"""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent
ROOT = BUILD.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(BUILD / "sources"))

import athletes  # noqa: E402
import build  # noqa: E402
import fis  # noqa: E402
import raceday  # noqa: E402
import results  # noqa: E402
import standings  # noqa: E402
import telkku  # noqa: E402
from classify import Classifier  # noqa: E402

FIX = HERE / "fixtures"
TOPICS = json.loads((ROOT / "config" / "topics.json").read_text(encoding="utf-8"))
SOURCES = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
EVENTS = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]


class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.c = Classifier(TOPICS)

    def test_real_titles(self):
        cases = {
            "Maastohiihto: Tour de Ski, N 10 km (p) Ruka": "hiihto",
            "Hiihdon Suomen cup: Sprintit (p)": "hiihto",
            "Hiihdon MM-kisat: Naisten sprintti": "hiihto",
            "Ampumahiihdon maailmancup: Pariviesti, Kontiolahti": "ampumahiihto",
            "Yhdistetyn maailmancup: M 10 km Ruka": "yhdistetty",
            "Yhdistetyn maailmancup: M yhteislähtö Ruka": "yhdistetty",
            "Yhdistetyn maailmancup: M HS 142 Ruka": None,          # mäkiosuus
            "Mäkihypyn maailmancup: HS 142, Ruka": None,
            "Alppihiihdon maailmancup, naisten suurpujottelun 2. kierros.": None,
            "Urheilustudio: 28.11.2026 09:30.": None,
            "Uinnin MM: Kooste 1. kilpailupäivän alkueräuinneista": None,
            "Hiihdon MM-kisat: Kooste": None,
            "Lumilautailun maailmancup: Parisuurpujottelu": None,
            "Rikoksen aakkoset (12)": None,
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(self.c.classify(title), expected)


class TestFis(unittest.TestCase):
    def test_parse_nk_fixture(self):
        races = fis.parse_races((FIX / "fis_nk_wsc.ics").read_text(encoding="utf-8"), "NK")
        self.assertEqual(len(races), 7)
        first = min(races, key=lambda r: r["date"])
        self.assertEqual(first["date"], "2027-02-25")
        self.assertEqual(first["place"], "Falun")
        self.assertTrue(first["url"].startswith("https://www.fis-ski.com/"))

    def test_translate(self):
        self.assertEqual(fis.translate_name("10km Interval Start Classic"), "10 km väliaikalähtö (p)")
        self.assertEqual(fis.translate_name("1.4km Sprint Qualification Free"), "1,4 km sprintin karsinta (v)")
        self.assertEqual(fis.translate_name("2x4.5km Team Sprint Classic"), "2x4,5 km parisprintti (p)")
        self.assertEqual(fis.translate_name("20km Skiathlon Classic/Free"), "20 km yhdistelmähiihto (p/v)")

    def test_ski_leg_filter(self):
        self.assertTrue(build.has_ski_leg("Individual Gundersen Large Hill/10 km"))
        self.assertFalse(build.has_ski_leg("Large Hill"))


class TestTelkku(unittest.TestCase):
    def test_fixture_to_broadcasts(self):
        payload = json.loads((FIX / "telkku_2026-11-28.json").read_text(encoding="utf-8"))
        cfg = SOURCES["telkku"]
        programs, total = telkku.parse_offering(payload, set(cfg["channels"]))
        self.assertGreater(total, 0)
        topics_by_id = {t["id"]: t for t in TOPICS["topics"]}
        bcs = build.build_broadcasts(programs, cfg, Classifier(TOPICS), topics_by_id, EVENTS, ZoneInfo("Europe/Helsinki"))
        got = [(b["start"][11:16], b["topic"], b["event_id"]) for b in bcs]
        self.assertEqual(got, [
            ("09:40", "hiihto", "2026-ruka-mc"),
            ("12:10", "hiihto", "2026-ruka-mc"),
            ("14:05", "ampumahiihto", "2026-kontiolahti-amh"),
            ("15:25", "yhdistetty", "2026-ruka-mc"),
            ("16:10", "ampumahiihto", "2026-kontiolahti-amh"),
        ])
        self.assertTrue(all(b["channel"] == "Yle TV2" for b in bcs))
        self.assertEqual(bcs[0]["title"], "Maastohiihto: Sprinttikarsinnat (p) Ruka")
        self.assertFalse(any("Tour de Ski" in b["title"] for b in bcs))

    def test_clean_title(self):
        ruka = next(e for e in EVENTS if e["id"] == "2026-ruka-mc")
        self.assertEqual(build.clean_title("Maastohiihto: Tour de Ski, N 10 km (p) Ruka", ruka),
                         "Maastohiihto: N 10 km (p) Ruka")
        tds = dict(ruka, tour_de_ski=True)
        self.assertIn("Tour de Ski", build.clean_title("Maastohiihto: Tour de Ski, N 10 km (p)", tds))
        self.assertIn("Tour de Ski", build.clean_title("Maastohiihto: Tour de Ski, N 10 km (p)", None))


class TestNonYle(unittest.TestCase):
    def race(self, uid, d, place, cat="World Cup"):
        return {"uid": uid, "date": d, "discipline": "CC", "category": cat, "place": place,
                "gender": "N", "name": "10km", "name_fi": "10 km", "url": ""}

    def test_grouping(self):
        races = [
            self.race("1", "2026-11-28", "Ruka"),                       # Ylen tapahtuma → ei mukaan
            self.race("2", "2026-12-11", "Davos"), self.race("3", "2026-12-13", "Davos"),
            self.race("4", "2027-01-01", "Les Rousses", "Stage World Cup"),
            self.race("5", "2027-01-08", "Val di Fiemme", "Stage World Cup"),
            self.race("6", "2027-01-01", "FIS Tour de Ski"),           # kokonaispisteet → ohitetaan
        ]
        _, used = build.attach_races(EVENTS, races)
        out = build.non_yle_events(races, used)
        self.assertEqual([(e["place"], e["start"], e["end"], len(e["races"])) for e in out], [
            ("Davos", "2026-12-11", "2026-12-13", 2),
            ("Tour de Ski", "2027-01-01", "2027-01-08", 2),
        ])
        self.assertTrue(all(e["broadcaster"] == "other" for e in out))


class TestMatching(unittest.TestCase):
    def test_ruka_sc_vs_mc(self):
        self.assertEqual(build.match_event(EVENTS, "hiihto", date(2026, 11, 22), "Hiihdon Suomen cup: Sprintit"), "2026-ruka-sc")
        self.assertEqual(build.match_event(EVENTS, "hiihto", date(2026, 11, 28), "Sprintti Ruka"), "2026-ruka-mc")

    def test_no_match_outside_events(self):
        self.assertIsNone(build.match_event(EVENTS, "hiihto", date(2026, 12, 20), "Maastohiihto: jotain"))


class TestStandings(unittest.TestCase):
    def test_fis_overall(self):
        r = standings.parse_fis((FIX / "fis_cup_cc_2026_m.html").read_text(encoding="utf-8"), "2026")
        self.assertEqual((r["done"], r["total"]), (42, 42))
        self.assertEqual(r["rows"][0], {
            "rank": 1, "name": "Johannes Hoesflot Klaebo", "nation": "NOR", "points": 2301,
            "url": "https://www.fis-ski.com/DB/general/athlete-biography.html?sectorcode=CC&competitorid=184205&type=cups&cupcode=WC"})
        trimmed = standings.trim(r["rows"])
        self.assertEqual(len(trimmed), 11)                       # kärki-10 + paras suomalainen
        self.assertEqual((trimmed[-1]["rank"], trimmed[-1]["name"], trimmed[-1]["nation"]), (22, "Lauri Vuorinen", "FIN"))

    def test_fis_wrong_cup_or_season(self):
        # ennen kauden 1. MC-kisaa FIS näyttää toisen cupin → ei dataa
        page = (FIX / "fis_cup_nk_2027_offseason.html").read_text(encoding="utf-8")
        self.assertIsNone(standings.parse_fis(page, "2027"))
        cc = (FIX / "fis_cup_cc_2026_m.html").read_text(encoding="utf-8")
        self.assertIsNone(standings.parse_fis(cc, "2027"))       # kausi ei täsmää

    def test_display_name(self):
        self.assertEqual(standings.display_name("NISKANEN Iivo"), "Iivo Niskanen")
        self.assertEqual(standings.display_name("DE CAMPO Seve"), "Seve De Campo")
        self.assertEqual(standings.display_name("WALKER-BROOSE Bentley"), "Bentley Walker-Broose")

    def test_wiki_biathlon(self):
        p = standings.parse_wiki((FIX / "wiki_biathlon_2025-26.txt").read_text(encoding="utf-8"))
        self.assertEqual(set(p), {"M", "N"})
        self.assertEqual((p["M"]["done"], p["M"]["total"], len(p["M"]["rows"])), (21, 21, 10))
        self.assertEqual({k: p["M"]["rows"][0][k] for k in ("rank", "name", "nation", "points")},
                         {"rank": 1, "name": "Éric Perrot", "nation": "FRA", "points": 1263})
        self.assertEqual(p["N"]["rows"][0]["name"], "Lou Jeanmonnot")

    def test_wiki_empty_season(self):
        p = standings.parse_wiki((FIX / "wiki_biathlon_2026-27.txt").read_text(encoding="utf-8"))
        self.assertEqual((p["M"]["done"], p["M"]["rows"]), (0, []))

    def test_wiki_title(self):
        self.assertEqual(standings.wiki_title("2027"), "2026–27 Biathlon World Cup")


class TestAthletes(unittest.TestCase):
    def page(self, name):
        return (FIX / name).read_text(encoding="utf-8")

    def test_bio(self):
        self.assertEqual(athletes.parse_bio(self.page("fis_athlete_150212_wc_2026.html")),
                         {"club": "Puijon Hiihtoseura", "birthdate": "1992-01-12"})

    def test_season_results(self):
        res = athletes.parse_results(self.page("fis_athlete_150212_wc_2026.html"))
        self.assertEqual(len(res), 10)
        self.assertEqual(res[0], {"raceid": "49517", "date": "2026-03-08", "place": "Lahti",
                                  "category": "World Cup", "race": "Interval Start", "rank": 5})
        self.assertEqual(res[2]["category"], "Stage World Cup")            # Tour de Ski mukana
        self.assertEqual(res[2]["rank"], 10)                               # "10 (27)" → 10
        self.assertIn("DNS", [r["rank"] for r in res])
        self.assertEqual(res, sorted(res, key=lambda r: r["date"], reverse=True))

    def test_empty_season(self):
        self.assertEqual(athletes.parse_results(self.page("fis_athlete_150212_wc_2027_empty.html")), [])

    def test_broken_page(self):
        with self.assertRaises(RuntimeError):
            athletes.parse_results("<html>huoltokatko</html>")
        with self.assertRaises(RuntimeError):
            athletes.parse_podiums("<html></html>")

    def test_career(self):
        self.assertEqual(athletes.parse_podiums(self.page("fis_athlete_150212_podiums.html")), {"wins": 10, "podiums": 26})

    def test_medals(self):
        ol = athletes.count_medals(athletes.parse_results(self.page("fis_athlete_150212_owg.html")))
        mm = athletes.count_medals(athletes.parse_results(self.page("fis_athlete_150212_wsc.html")))
        self.assertEqual(ol, {"g": 3, "s": 1, "b": 1})                    # parisprintti 2014 mukana
        self.assertEqual(mm, {"g": 1, "s": 1, "b": 2})

    def test_race_label(self):
        r = {"raceid": "1", "race": "Sprint Final"}
        self.assertEqual(athletes.race_label(r, {}), "sprintti")
        self.assertEqual(athletes.race_label(r, {"1": "1,2 km sprintin finaalit (p)"}), "1,2 km sprintti (p)")
        self.assertEqual(athletes.race_label({"raceid": "2", "race": "Heat Mass Start"}, {}), "yhteislähtö (erät)")

    def test_wikidata(self):
        wd = athletes.parse_wikidata(json.loads(self.page("wikidata_p2773.json")))
        self.assertEqual(wd["150212"], {"wiki_url": "https://fi.wikipedia.org/wiki/Iivo_Niskanen", "birthplace": "Oulu"})
        self.assertIn("184205", wd)

    def test_summary(self):
        text = athletes.parse_summary(json.loads(self.page("wiki_summary_iivo.json")))
        self.assertTrue(text.startswith("Iivo Henrik Niskanen"))
        self.assertIsNone(athletes.parse_summary({"type": "disambiguation", "extract": "x"}))
        long = "Ensimmäinen virke on tässä ja se on aika pitkä. " * 4 + "Viimeinen."
        short = athletes.shorten(long, 120)
        self.assertTrue(short.endswith("pitkä.") and len(short) <= 120)

    def test_targets_only_cross_country(self):
        mk = lambda topic, cid, pts: {"id": f"{topic}-M", "topic": topic,
                                      "rows": [{"points": pts, "url": f"https://x/?competitorid={cid}&type=cups"}]}
        t = athletes.targets([mk("hiihto", "1", 100), mk("yhdistetty", "2", 50), mk("ampumahiihto", "3", 10)])
        self.assertEqual([x["id"] for x in t], ["1"])

    def test_champs_window(self):
        ev = [{"type": "MM", "start": "2027-02-17", "end": "2027-03-01"}, {"type": "MC", "start": "2026-11-27", "end": "2026-11-29"}]
        self.assertTrue(athletes.champs_active(ev, date(2027, 3, 2)))
        self.assertFalse(athletes.champs_active(ev, date(2026, 11, 28)))

    def test_refresh_reuses_previous(self):
        """Pisteet ennallaan ja tieto tuore → ei hakuja; pudonnut hiihtäjä jää pois."""
        from datetime import datetime
        now = datetime(2026, 12, 1, 6, 0)
        stamp = now.isoformat(timespec="minutes")
        prev = {"1": {"id": "1", "points": 100, "season_code": "2027", "updated": stamp, "medals_updated": stamp,
                      "wiki_checked": stamp, "career": {"wins": 1, "podiums": 2}},
                "9": {"id": "9", "points": 5}}
        lists = [{"id": "hiihto-M", "topic": "hiihto", "rows": [{"points": 100, "url": "?competitorid=1"}]}]
        orig = athletes.fetch
        athletes.fetch = lambda url: (_ for _ in ()).throw(AssertionError(f"ei pitänyt hakea: {url}"))
        try:
            prof, err = athletes.fetch_profiles(lists, prev, "2027", {}, now, champs=False, delay=0)
        finally:
            athletes.fetch = orig
        self.assertEqual(err, {})
        self.assertEqual(list(prof), ["1"])
        self.assertEqual(prof["1"]["career"], {"wins": 1, "podiums": 2})

    def test_failed_fetch_keeps_previous(self):
        from datetime import datetime
        now = datetime(2026, 12, 1, 6, 0)
        prev = {"1": {"id": "1", "points": 50, "season_code": "2027", "updated": "2026-11-30T06:00",
                      "career": {"wins": 1, "podiums": 2}}}
        lists = [{"id": "hiihto-M", "topic": "hiihto", "rows": [{"points": 100, "url": "?competitorid=1"},
                                                                {"points": 90, "url": "?competitorid=2"}]}]
        orig = athletes.fetch
        athletes.fetch = lambda url: (_ for _ in ()).throw(RuntimeError("verkkovirhe"))
        try:
            prof, err = athletes.fetch_profiles(lists, prev, "2027", {}, now, champs=False, delay=0)
        finally:
            athletes.fetch = orig
        self.assertEqual(prof["1"]["career"], {"wins": 1, "podiums": 2})   # vanha säilyy
        self.assertNotIn("2", prof)                                        # uusi ilman dataa → ei profiilia
        self.assertIn("1", err)


class TestRaceDay(unittest.TestCase):
    DATA = {"events": [
        {"type": "MC", "start": "2026-11-27", "end": "2026-11-29",
         "races": [{"date": "2026-11-27"}, {"date": "2026-11-29"}]},
        {"type": "MC", "start": "2026-11-26", "end": "2026-11-26", "races": []},   # ampumahiihto
        {"type": "SC", "start": "2026-11-21", "end": "2026-11-22", "races": [{"date": "2026-11-21"}]},
        {"type": "OL", "start": "2026-12-10", "end": "2026-12-12", "races": []},
    ]}

    def test_days(self):
        self.assertTrue(raceday.is_race_day(self.DATA, "2026-11-26"))
        self.assertTrue(raceday.is_race_day(self.DATA, "2026-11-27"))
        self.assertFalse(raceday.is_race_day(self.DATA, "2026-11-28"))   # lepopäivä tapahtuman sisällä
        self.assertTrue(raceday.is_race_day(self.DATA, "2026-11-21"))    # Suomen cup
        self.assertTrue(raceday.is_race_day(self.DATA, "2026-11-22"))    # SC: tapahtuman päivät, ei kisalista
        self.assertFalse(raceday.is_race_day(self.DATA, "2026-11-23"))
        self.assertFalse(raceday.is_race_day(self.DATA, "2026-12-11"))   # muu tyyppi


class TestResults(unittest.TestCase):
    def fix(self, name):
        return (FIX / name).read_text(encoding="utf-8")

    def test_fis_distance(self):
        r = results.parse_fis(self.fix("fis_results_49517_distance.html"))
        self.assertEqual(r["kind"], "Men's 10km Interval Start Classic")
        self.assertEqual(len(r["rows"]), 30)
        self.assertEqual(r["rows"][0], {"rank": 1, "name": "Johannes Hoesflot Klaebo", "nat": "NOR", "time": "23:22.6"})
        self.assertEqual(r["rows"][1]["diff"], "+22.1")
        self.assertEqual(r["rows"][7], {"rank": 8, "name": "Ville Ahonen", "nat": "FIN", "time": "24:16.0", "diff": "+53.4"})

    def test_fis_sprint_phases(self):
        rows = results.parse_fis(self.fix("fis_results_49535_sprint.html"))["rows"]
        self.assertEqual([r["phase"] for r in rows[:1] + rows[6:7] + rows[12:13] + rows[29:30]],
                         ["Finaali", "Välierä", "Puolivälierä", "Puolivälierä"])
        self.assertNotIn("time", rows[0])
        self.assertEqual(len(rows), 30)                    # karsiutuneet (31.–) eivät tule mukaan

    def test_fis_relay(self):
        rows = results.parse_fis(self.fix("fis_results_41653_relay.html"))["rows"]
        self.assertEqual(rows[0]["name"], "Norway")
        self.assertEqual(rows[0]["members"], ["Holund", "Golberg", "Krueger", "Klaebo"])
        self.assertEqual(rows[1]["nat"], "FIN")
        self.assertEqual(rows[1]["diff"], "+46.9")

    def test_fis_not_held_and_broken(self):
        page = self.fix("fis_results_49517_distance.html")
        empty = page[:page.find('<a class="table-row')]
        self.assertIsNone(results.parse_fis(empty))
        with self.assertRaises(ValueError):
            results.parse_fis("<html>muuttunut sivu</html>")

    def test_pdf_sprint(self):
        r = results.parse_eq_pdf(self.fix("sc_ruka_2026_m_sprint.txt"))
        self.assertEqual((r["gender"], r["name"], r["date"], r["kind"]), ("M", "1,4 km sprintti (p)", "2026-11-21", "sprint"))
        self.assertEqual(r["rows"][0], {"rank": 1, "name": "Lauri Vuorinen", "club": "Ounasvaaran Hiihtoseura", "phase": "Finaali"})
        self.assertEqual(r["rows"][2]["name"], "Ville Ahonen")               # huomautus samalla rivillä
        self.assertEqual(r["rows"][6]["phase"], "Välierä")
        self.assertEqual(r["rows"][12]["phase"], "Puolivälierä")
        self.assertEqual(len(r["rows"]), 30)
        self.assertEqual(r["ranked"], 78)

    def test_fis_final_times(self):
        times = results.parse_fis_final_pdf(self.fix("fis_results_49535_sprint_pdf.txt"))
        self.assertEqual(times, {1: {"time": "2:28.82"}, 2: {"diff": "+0.13"}, 3: {"diff": "+0.80"},
                                 4: {"diff": "+1.28"}, 5: {"diff": "+2.52"}, 6: {"diff": "+10.43"}})
        page = (FIX / "fis_results_49535_sprint.html").read_text(encoding="utf-8")
        rows = results.parse_fis(page)["rows"]
        self.assertEqual(results.add_final_times(rows, times, lambda i, row: row["rank"]), 6)
        self.assertEqual(rows[0]["time"], "2:28.82")
        self.assertEqual(rows[5]["diff"], "+10.43")
        self.assertNotIn("diff", rows[6])                  # välieräläiset ilman aikaa
        self.assertEqual(results.parse_fis_final_pdf("ei finaalia"), {})

    def test_fis_final_dnf_uses_column(self):
        text = """Final
      1     1 KLAEBO Johannes                  NOR   2:27.15   (1)   2:30.43(1)        2:28.40(1)        2:28.82(1)
      6     7 RIEBLI Janik                     SUI   2:30.04   (7)   2:28.80(PF1)      +0.56(4)
Semifinals
"""
        self.assertEqual(results.parse_fis_final_pdf(text), {1: {"time": "2:28.82"}})

    def test_live_final(self):
        times = results.parse_live_final(self.fix("live_ruka_2026_m_final.html"))
        self.assertEqual(times["6"], {"time": "2:34.88"})          # Lauri Vuorinen, numero 6
        self.assertEqual(times["9"], {"diff": "+4.61"})
        self.assertEqual(len(times), 6)
        r = results.parse_eq_pdf(self.fix("sc_ruka_2026_m_sprint.txt"))
        results.add_final_times(r["rows"], times, lambda i, row: r["bibs"][i])
        self.assertEqual(r["rows"][0], {"rank": 1, "name": "Lauri Vuorinen", "club": "Ounasvaaran Hiihtoseura",
                                        "phase": "Finaali", "time": "2:34.88"})
        self.assertEqual(r["rows"][1]["diff"], "+2.11")
        self.assertNotIn("diff", r["rows"][6])

    def test_live_wrong_event(self):
        orig = results.fetch
        results.fetch = lambda *a, **k: "<title>Maastohiihdon Suomen Cup 22.-23.11.2025 Ruka</title>".encode("iso-8859-1")
        try:
            with self.assertRaises(ValueError):
                results.fetch_live_finals({"start": "2026-11-21", "live_results": "https://x/"}, delay=0)
        finally:
            results.fetch = orig

    def test_pdf_distance(self):
        r = results.parse_eq_pdf(self.fix("sc_tampere_2026_m_15km.txt"))
        self.assertEqual((r["gender"], r["name"], r["date"], r["kind"]), ("M", "15 km (p)", "2026-01-31", "distance"))
        self.assertEqual(r["rows"][0], {"rank": 1, "name": "Ari Luusua", "club": "Tampereen Yritys", "time": "32:12.7"})
        self.assertEqual(r["rows"][1]["diff"], "+27.0")
        self.assertEqual(r["rows"][25]["club"], "Kuusamon Erä-Veikot")      # "Erä" seuran nimessä ei ole sprintin vaihe
        self.assertNotIn("phase", r["rows"][25])

    def test_pdf_relay(self):
        r = results.parse_eq_pdf(self.fix("sc_vuokatti_2026_m_relay.txt"))
        self.assertEqual(r["kind"], "relay")
        self.assertEqual(r["rows"][2], {"rank": 3, "name": "Puijon Hiihtoseura", "time": "1:10:54.7", "diff": "+1.1",
                                        "members": ["Heikkinen", "Niskanen", "Mäkinen"]})

    def test_pdf_garbage(self):
        with self.assertRaises(ValueError):
            results.parse_eq_pdf("Suomen Cup\nLähtölista\n")
        with self.assertRaises(ValueError):
            results.pdf_to_text(b"<!doctype html>404")

    def test_pdf_links(self):
        page = """<a href="/wp-content/uploads/2026/11/m_spr_karsinta_res.pdf">Miesten sprintin karsinnan tulokset</a>
          <a href="https://hiihtoliitto.fi/wp-content/uploads/2026/11/m_spr_lopputulokset_4.pdf">Miesten sprintin lopputulokset</a>
          <a href="https://hiihtoliitto.fi/wp-content/uploads/2026/11/m_spr_lopputulokset_4.pdf">Miesten sprintti</a>
          <a href="https://hiihtoliitto.fi/wp-content/uploads/2026/10/sprinttikaavio_30hiihtajaa.pdf">Sprinttikaavio</a>
          <a href="https://hiihtoliitto.fi/wp-content/uploads/2026/01/m_15km_res.pdf">Miehet 15 km</a>
          <a href="https://hiihtoliitto.fi/wp-content/uploads/2026/11/Kilpailuohje.pdf">Kilpailuohje</a>"""
        links = results.pdf_links(page, "https://hiihtoliitto.fi/tapahtumat/suomen-cup/ruka/")
        self.assertEqual([u.rsplit("/", 1)[-1] for u, _ in links], ["m_spr_lopputulokset_4.pdf", "m_15km_res.pdf"])

    def test_due(self):
        now = date(2026, 11, 30)
        url = "https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid=52085"
        race = {"date": "2026-11-27", "discipline": "CC", "name_fi": "10 km väliaikalähtö (p)", "url": url}
        self.assertTrue(results.due(race, {}, now))                                   # puuttuu → haetaan
        self.assertTrue(results.due(race, {"fis-CC-52085": {}}, date(2026, 11, 29)))  # 2 pv korjauksille
        self.assertFalse(results.due(race, {"fis-CC-52085": {}}, now))                # jäädytetty
        self.assertFalse(results.due(dict(race, date="2026-12-01"), {}, now))         # tuleva kisa
        self.assertFalse(results.due(dict(race, name_fi="1,4 km sprintin karsinta (v)"), {}, now))

    def test_sc_due(self):
        ev = {"type": "SC", "start": "2026-11-21", "end": "2026-11-22", "results_page": "x"}
        self.assertFalse(results.sc_due(ev, [], date(2026, 11, 20)))
        self.assertTrue(results.sc_due(ev, [], date(2026, 11, 21)))
        self.assertTrue(results.sc_due(ev, [{"res": "a"}], date(2026, 11, 24)))
        self.assertFalse(results.sc_due(ev, [{"res": "a"}], date(2026, 11, 25)))     # jäädytetty
        self.assertTrue(results.sc_due(ev, [], date(2026, 12, 10)))                  # puuttuvia etsitään vielä
        self.assertFalse(results.sc_due(ev, [], date(2027, 1, 10)))
        self.assertFalse(results.sc_due(dict(ev, results_page=None), [], date(2026, 11, 21)))
        prev = {"a": {"kind": "sprint", "rows": [{"rank": 1, "phase": "Finaali"}]}}
        live = dict(ev, live_results="https://x/")
        self.assertTrue(results.sc_due(live, [{"res": "a"}], date(2026, 11, 30), prev))   # finaaliajat puuttuvat
        self.assertFalse(results.sc_due(ev, [{"res": "a"}], date(2026, 11, 30), prev))    # ei live-palvelua
        prev["a"]["rows"][0]["time"] = "2:34.88"
        self.assertFalse(results.sc_due(live, [{"res": "a"}], date(2026, 11, 30), prev))

    def test_fetch_keeps_old_on_error(self):
        url = "https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid=52085"
        race = {"date": "2026-11-29", "discipline": "CC", "name_fi": "10 km", "url": url}
        prev = {"fis-CC-52085": {"rows": [{"rank": 1}]}, "fis-CC-1": {"rows": []}}
        orig = results.fetch
        results.fetch = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("verkko"))
        try:
            from datetime import datetime
            out, err = results.fetch_fis_results([race], prev, datetime(2026, 11, 30, 12, tzinfo=ZoneInfo("Europe/Helsinki")), delay=0)
        finally:
            results.fetch = orig
        self.assertEqual(out["fis-CC-52085"], prev["fis-CC-52085"])
        self.assertIn("fis-CC-1", out)
        self.assertIn("fis-CC-52085", err)


if __name__ == "__main__":
    unittest.main()
