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

import build  # noqa: E402
import fis  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
