# -*- coding: utf-8 -*-
"""Parser odpowiedzi strumieniowych – bez Qt.

Formaty: SSE Anthropic/OpenAI, NDJSON Ollama.
"""
import json

from gis_assistant_ai.stream import StreamParser


def sse(*events):
    return "".join("event: %s\ndata: %s\n\n"
                   % (e.get("type", "x"), json.dumps(e))
                   for e in events).encode("utf-8")


ANTHROPIC_EVENTS = [
    {"type": "message_start",
     "message": {"id": "msg_1", "role": "assistant", "content": []}},
    {"type": "content_block_start", "index": 0,
     "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0,
     "delta": {"type": "text_delta", "text": "Szukam adresu usługi… "}},
    {"type": "content_block_stop", "index": 0},
    {"type": "content_block_start", "index": 1,
     "content_block": {"type": "server_tool_use", "id": "srvtoolu_1",
                       "name": "web_search", "input": {}}},
    {"type": "content_block_delta", "index": 1,
     "delta": {"type": "input_json_delta",
               "partial_json": '{"query": "parki '}},
    {"type": "content_block_delta", "index": 1,
     "delta": {"type": "input_json_delta", "partial_json": 'narodowe WMS"}'}},
    {"type": "content_block_stop", "index": 1},
    {"type": "content_block_start", "index": 2,
     "content_block": {"type": "web_search_tool_result",
                       "tool_use_id": "srvtoolu_1", "content": []}},
    {"type": "content_block_stop", "index": 2},
    {"type": "content_block_start", "index": 3,
     "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 3,
     "delta": {"type": "text_delta", "text": '{"type":"plan"'}},
    {"type": "content_block_delta", "index": 3,
     "delta": {"type": "citations_delta",
               "citation": {"type": "web_search_result_location",
                            "url": "https://sdi.gdos.gov.pl"}}},
    {"type": "content_block_delta", "index": 3,
     "delta": {"type": "text_delta", "text": ',"steps":[]}'}},
    {"type": "content_block_stop", "index": 3},
    {"type": "message_delta", "delta": {"stop_reason": "end_turn"},
     "usage": {"output_tokens": 42}},
    {"type": "message_stop"},
]


class TestAnthropic:
    """SSE Anthropic: tekst, web_search, bloki do wznowienia tury."""

    def test_text_search_and_blocks(self):
        p = StreamParser("anthropic")
        found = p.feed(sse(*ANTHROPIC_EVENTS))
        p.flush()
        assert found == ["parki narodowe WMS"]
        assert (p.result_text()
                == 'Szukam adresu usługi… {"type":"plan","steps":[]}')
        assert (p.stop_reason == "end_turn" and not p.truncated
                and p.error is None)
        # bloki odtworzone w kolejności i nadające się do odesłania
        # (pause_turn)
        content = p.continuation_content()
        assert [b["type"] for b in content] == [
            "text", "server_tool_use", "web_search_tool_result", "text"]
        assert content[1]["input"] == {"query": "parki narodowe WMS"}
        assert content[3]["text"] == '{"type":"plan","steps":[]}'
        assert (content[3]["citations"][0]["url"]
                == "https://sdi.gdos.gov.pl")

    def test_chunks_split_mid_line(self):
        raw = sse(*ANTHROPIC_EVENTS)
        p = StreamParser("anthropic")
        searches = []
        # dowolne cięcie bajtów – także w środku znaków UTF-8
        for i in range(0, len(raw), 7):
            searches += p.feed(raw[i:i + 7])
        p.flush()
        assert searches == ["parki narodowe WMS"]
        assert (p.result_text()
                == 'Szukam adresu usługi… {"type":"plan","steps":[]}')
        assert p.chars() == len(p.result_text())

    def test_pause_turn_and_max_tokens(self):
        p = StreamParser("anthropic")
        p.feed(sse({"type": "message_delta",
                    "delta": {"stop_reason": "pause_turn"}}))
        assert p.stop_reason == "pause_turn" and not p.truncated
        p = StreamParser("anthropic")
        p.feed(sse({"type": "content_block_delta", "index": 0,
                    "delta": {"type": "text_delta", "text": "{"}},
                   {"type": "message_delta",
                    "delta": {"stop_reason": "max_tokens"}}))
        assert p.truncated and p.result_text() == "{\n"

    def test_stream_error(self):
        p = StreamParser("anthropic")
        p.feed(sse({"type": "error",
                    "error": {"type": "overloaded_error",
                              "message": "Overloaded"}}))
        assert p.error == "Overloaded"

    def test_broken_tool_input_json(self):
        p = StreamParser("anthropic")
        p.feed(sse({"type": "content_block_start", "index": 0,
                    "content_block": {"type": "server_tool_use",
                                      "name": "web_search", "input": {}}},
                   {"type": "content_block_delta", "index": 0,
                    "delta": {"type": "input_json_delta",
                              "partial_json": '{"query": '}},
                   {"type": "content_block_stop", "index": 0}))
        assert p.blocks[0]["input"] == {} and p.searches == []

    def test_complete_non_streamed(self):
        p = StreamParser("anthropic")
        text = p.complete(json.dumps({
            "content": [{"type": "server_tool_use", "name": "web_search",
                         "input": {"query": "TERYT Lesznowola"}},
                        {"type": "web_search_tool_result", "content": []},
                        {"type": "text",
                         "text": '{"type":"answer","text":"141805_2"}'}],
            "stop_reason": "end_turn"}))
        assert text == '{"type":"answer","text":"141805_2"}'
        assert (p.searches == ["TERYT Lesznowola"]
                and len(p.continuation_content()) == 3)

    def test_unfinished_block_and_chars(self):
        p = StreamParser("anthropic")
        p.feed(sse({"type": "content_block_start", "index": 0,
                    "content_block": {"type": "text", "text": "Ab"}},
                   {"type": "content_block_delta", "index": 0,
                    "delta": {"type": "text_delta", "text": "cd"}},
                   {"type": "content_block_delta", "index": 0,
                    "delta": {"type": "text_delta", "text": "ę"}}))
        assert p.chars() == 5 and p.result_text() == "Abcdę"
        assert p.continuation_content() == [{"type": "text",
                                             "text": "Abcdę"}]
        p.complete(json.dumps({"content": [{"type": "text", "text": "xyz"}],
                               "stop_reason": "end_turn"}))
        assert p.chars() == 3

    def test_ignores_comments_and_garbage(self):
        p = StreamParser("anthropic")
        p.feed(b": keep-alive\n\nevent: ping\ndata: not json\n\n"
               b"data: [DONE]\n\ndata: 42\n\n")
        assert p.result_text() == "" and p.error is None


class TestOpenAI:
    """SSE OpenAI: choices[].delta, ucięcie, odpowiedź pełna, błąd."""

    def test_stream(self):
        p = StreamParser("openai")
        p.feed(b'data: {"choices":[{"delta":{"role":"assistant",'
               b'"content":""}}]}\n'
               b'data: {"choices":[{"delta":{"content":"{\\"type\\":"}}]}\n'
               b'data: {"choices":[{"delta":{"content":"\\"answer\\"}"},'
               b'"finish_reason":"stop"}]}\n'
               b'data: [DONE]\n')
        assert p.result_text() == '{"type":"answer"}' and not p.truncated

    def test_truncated(self):
        p = StreamParser("openai")
        p.feed(b'data: {"choices":[{"delta":{"content":"{"},'
               b'"finish_reason":"length"}]}\n')
        assert p.truncated and p.result_text().endswith("\n")

    def test_complete(self):
        p = StreamParser("openai")
        assert p.complete('{"choices":[{"message":{"content":"{}"},'
                          '"finish_reason":"stop"}]}') == "{}"
        assert p.complete('{"choices":[{"message":{"content":null},'
                          '"finish_reason":"stop"}]}') == ""

    def test_error_object(self):
        p = StreamParser("openai")
        p.feed(b'data: {"error":{"message":"Rate limit",'
               b'"type":"rate_limit"}}\n')
        assert p.error == "Rate limit"


class TestOllama:
    """NDJSON Ollamy."""

    def test_ndjson(self):
        p = StreamParser("ollama")
        p.feed(b'{"message":{"role":"assistant","content":"{\\"type\\""},'
               b'"done":false}\n'
               b'{"message":{"role":"assistant","content":":\\"answer\\"}"},'
               b'"done":true,"done_reason":"stop"}')
        p.flush()   # ostatnia linia bez \n
        assert p.result_text() == '{"type":"answer"}' and not p.truncated

    def test_truncated_and_complete(self):
        p = StreamParser("ollama")
        p.feed(b'{"message":{"content":"x"},"done":true,'
               b'"done_reason":"length"}\n')
        assert p.truncated
        assert StreamParser("ollama").complete(
            '{"message":{"content":"ok"}}') == "ok"

    def test_unknown_provider(self):
        import pytest
        with pytest.raises(ValueError):
            StreamParser("other").complete("{}")
