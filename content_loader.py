"""Loads curriculum content and exposes flat lookups used by the bot."""
import json
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"


class Curriculum:
    def __init__(self):
        self.index = json.loads((CONTENT_DIR / "index.json").read_text())
        self.module_order = self.index["module_order"]
        self.modules = self.index["modules"]

        self.topics_by_module = {}   # module -> [topic, ...]
        self.topic_by_id = {}        # topic_id -> topic (with 'module' injected)
        self.ordered_topic_ids = []  # full sequence across modules

        for module in self.module_order:
            data = json.loads((CONTENT_DIR / self.modules[module]["file"]).read_text())
            topics = data["topics"]
            self.topics_by_module[module] = topics
            for t in topics:
                t["module"] = module
                self.topic_by_id[t["id"]] = t
                self.ordered_topic_ids.append(t["id"])

    # -- review item id helpers (stable strings stored in the DB) --
    @staticmethod
    def flashcard_item_id(topic_id, i):
        return f"{topic_id}:fc:{i}"

    @staticmethod
    def quiz_item_id(topic_id, i):
        return f"{topic_id}:quiz:{i}"

    def parse_item_id(self, item_id):
        """'spc-01:quiz:2' -> (topic, 'quiz', 2)."""
        topic_id, kind, i = item_id.rsplit(":", 2)
        topic = self.topic_by_id.get(topic_id)
        i = int(i)
        if topic is None:
            return None
        if kind == "fc":
            card = topic["flashcards"][i]
            return {"topic": topic, "kind": "flashcard", "q": card["q"], "a": card["a"]}
        else:
            q = topic["quiz"][i]
            return {"topic": topic, "kind": "quiz", **q}

    def all_item_ids_for_module(self, module):
        ids = []
        for t in self.topics_by_module[module]:
            for i in range(len(t.get("flashcards", []))):
                ids.append(self.flashcard_item_id(t["id"], i))
            for i in range(len(t.get("quiz", []))):
                ids.append(self.quiz_item_id(t["id"], i))
        return ids

    def module_title(self, module):
        return self.modules[module].get("blurb", module)

    def module_emoji(self, module):
        return self.modules[module].get("emoji", "•")
