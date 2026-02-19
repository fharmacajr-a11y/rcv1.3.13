from tkinter.scrolledtext import ScrolledText

HIT_TAG = "hit"


class SearchNavigator:
    def __init__(self, text: ScrolledText):
        self.text = text
        self.query = ""
        self.hits = []
        self.pos = -1
        self.text.tag_config(HIT_TAG, background="#ffd54f")
        self.text.tag_raise("sel")  # garante seleção visível sobre o highlight

    def set_query(self, q: str):
        q = (q or "").strip()
        if q == self.query:
            return
        self.query = q
        self._reindex()

    def _reindex(self):
        t = self.text
        t.tag_remove(HIT_TAG, "1.0", "end")
        self.hits.clear()
        if not self.query:
            self.pos = -1
            return
        start = "1.0"
        while True:
            idx = t.search(self.query, start, stopindex="end", nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(self.query)}c"
            t.tag_add(HIT_TAG, idx, end)
            self.hits.append((idx, end))
            start = end
        self.pos = -1

    def _goto(self, i: int):
        if not self.hits:
            return
        self.pos = i % len(self.hits)
        idx, end = self.hits[self.pos]
        self.text.see(idx)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", idx, end)

    def next(self):
        if self.hits:
            self._goto(self.pos + 1)

    def prev(self):
        if self.hits:
            self._goto(self.pos - 1)
