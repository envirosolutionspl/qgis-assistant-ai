# -*- coding: utf-8 -*-
"""Parser odpowiedzi strumieniowych modeli językowych – bez Qt, więc testowalny poza QGIS.

Obsługuje SSE Anthropic (zdarzenia content_block_*, message_delta, w tym bloki server_tool_use dla web_search
i wznawianie tury „pause_turn”), SSE OpenAI („data: {…}” z choices[].delta) i NDJSON Ollamy.
Ten sam obiekt odczytuje też odpowiedź niestrumieniową (complete()).
"""
import json

from .i18n import tr


class StreamParser:
    def __init__(self, provider):
        self.provider = provider
        self.text = []            # fragmenty tekstu odpowiedzi w kolejności nadejścia
        self.blocks = {}          # bloki odpowiedzi Anthropic (indeks → blok) – do wznowienia tury
        self.stop_reason = None
        self.truncated = False    # odpowiedź ucięta limitem tokenów
        self.error = None         # komunikat błędu przysłany w strumieniu ({"error": …})
        self.searches = []        # zapytania web_search wykryte w odpowiedzi (treść)
        self._partial = {}        # niepełny JSON wejścia narzędzia (input_json_delta)
        self._pending = b""       # niedokończona linia czekająca na kolejny fragment
        self._chars = 0           # łączna długość self.text (bez sumowania przy każdym fragmencie)
        self._block_text = {}     # fragmenty tekstu bloków Anthropic (indeks → lista), sklejane przy zamknięciu

    # ------------------------------------------------------------------ strumień
    def feed(self, chunk):
        """Dodaje fragment bajtów; zwraca listę zapytań web_search, które pojawiły się w tym fragmencie."""
        before = len(self.searches)
        data = self._pending + bytes(chunk)
        lines = data.split(b"\n")
        self._pending = lines.pop()
        for line in lines:
            self.line(line.decode("utf-8", "replace").strip())
        return self.searches[before:]

    def flush(self):
        """Koniec strumienia – przetwarza ostatnią linię bez znaku nowej linii."""
        if self._pending:
            self.line(self._pending.decode("utf-8", "replace").strip())
            self._pending = b""

    def chars(self):
        return self._chars

    def _add(self, piece):
        self.text.append(piece)
        self._chars += len(piece)

    def _set_text(self, pieces):
        self.text = pieces
        self._chars = sum(len(t) for t in pieces)

    def _join_block(self, idx):
        """Skleja fragmenty tekstu bloku w block["text"] (raz, zamiast doklejania przy każdym fragmencie)."""
        pieces = self._block_text.pop(idx, None)
        if pieces is not None and idx in self.blocks:
            self.blocks[idx]["text"] = "".join(pieces)

    def result_text(self):
        return "".join(self.text) + ("\n" if self.truncated else "")

    def line(self, line):
        """Linia SSE (Anthropic, OpenAI: „data: {…}”) lub NDJSON (Ollama)."""
        if not line or line.startswith((":", "event:")):
            return
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            return
        try:
            ev = json.loads(line)
        except ValueError:
            return
        if not isinstance(ev, dict):
            return
        if ev.get("error"):
            err = ev["error"]
            self.error = err.get("message") if isinstance(err, dict) else str(err)
            return
        if self.provider == "anthropic":
            self._anthropic_event(ev)
        elif self.provider == "openai":
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content")
                if piece:
                    self._add(piece)
                if ch.get("finish_reason") == "length":
                    self.truncated = True
        elif self.provider == "ollama":
            piece = (ev.get("message") or {}).get("content")
            if piece:
                self._add(piece)
            if ev.get("done_reason") == "length":
                self.truncated = True

    def _anthropic_event(self, ev):
        typ = ev.get("type")
        idx = ev.get("index")
        if typ == "content_block_start":
            self._block_text.pop(idx, None)
            self.blocks[idx] = dict(ev.get("content_block") or {})
            if self.blocks[idx].get("type") == "text":
                self.blocks[idx]["text"] = self.blocks[idx].get("text") or ""
                if self.blocks[idx]["text"]:
                    self._add(self.blocks[idx]["text"])
        elif typ == "content_block_delta":
            delta = ev.get("delta") or {}
            block = self.blocks.setdefault(idx, {"type": "text", "text": ""})
            if delta.get("type") == "text_delta":
                piece = delta.get("text", "")
                self._add(piece)
                self._block_text.setdefault(idx, [block.get("text") or ""]).append(piece)
            elif delta.get("type") == "input_json_delta":
                self._partial[idx] = self._partial.get(idx, "") + (delta.get("partial_json") or "")
            elif delta.get("type") == "citations_delta" and delta.get("citation"):
                block.setdefault("citations", []).append(delta["citation"])
        elif typ == "content_block_stop":
            self._join_block(idx)
            block = self.blocks.get(idx) or {}
            if idx in self._partial:
                try:
                    block["input"] = json.loads(self._partial.pop(idx) or "{}")
                except ValueError:
                    block["input"] = {}
            self._note_search(block)
        elif typ == "message_delta":
            reason = (ev.get("delta") or {}).get("stop_reason")
            if reason:
                self.stop_reason = reason
            if reason == "max_tokens":
                self.truncated = True

    def _note_search(self, block):
        if block.get("type") == "server_tool_use" and block.get("name") == "web_search":
            query = str((block.get("input") or {}).get("query") or "").strip()
            if query:
                self.searches.append(query[:200])

    # ------------------------------------------------------------------ odpowiedź niestrumieniowa
    def complete(self, raw):
        """Pełna odpowiedź JSON (bez stream) – zwraca tekst i ustawia blocks/stop_reason/truncated/searches."""
        data = json.loads(raw)
        if self.provider == "anthropic":
            content = [c for c in data.get("content", []) if isinstance(c, dict)]
            self.blocks = dict(enumerate(content))
            self._block_text = {}
            for c in content:
                self._note_search(c)
            self.stop_reason = data.get("stop_reason")
            self.truncated = self.stop_reason == "max_tokens"
            self._set_text([c.get("text", "") for c in content if c.get("type") == "text"])
            return self.result_text()
        if self.provider == "openai":
            choice = data["choices"][0]
            self._set_text([choice["message"]["content"] or ""])
            self.truncated = choice.get("finish_reason") == "length"
            return self.result_text()
        if self.provider == "ollama":
            self._set_text([data["message"]["content"]])
            self.truncated = data.get("done_reason") == "length"
            return self.result_text()
        raise ValueError(tr("nieznany dostawca"))

    def continuation_content(self):
        """Bloki odpowiedzi w postaci, którą API Anthropic przyjmie z powrotem jako treść asystenta (pause_turn)."""
        for idx in list(self._block_text):     # bloki bez content_block_stop (strumień urwany)
            self._join_block(idx)
        return [{k: v for k, v in self.blocks[i].items() if v is not None} for i in sorted(self.blocks)]
