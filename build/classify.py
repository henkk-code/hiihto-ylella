"""Lähetysten lajitunnistus config/topics.json -sääntöjen perusteella."""
import re


class Classifier:
    def __init__(self, topics_cfg: dict):
        flags = re.IGNORECASE
        self.global_exclude = [re.compile(p, flags) for p in topics_cfg.get("global_exclude", [])]
        self.topics = []
        for t in topics_cfg["topics"]:
            self.topics.append({
                "id": t["id"],
                "include": [re.compile(p, flags) for p in t["include"]],
                "exclude": [re.compile(p, flags) for p in t.get("exclude", [])],
            })

    def classify(self, title: str) -> str | None:
        """Palauttaa aiheen id:n tai None. Vain otsikko tarkistetaan (kuvaukset ovat liian vapaamuotoisia)."""
        if not title:
            return None
        if any(p.search(title) for p in self.global_exclude):
            return None
        for t in self.topics:
            if any(p.search(title) for p in t["include"]) and not any(p.search(title) for p in t["exclude"]):
                return t["id"]
        return None
