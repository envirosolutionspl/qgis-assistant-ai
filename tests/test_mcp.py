# -*- coding: utf-8 -*-
"""Serwer MCP: warstwa protokołu (bez Qt) i most stdio (uruchamiany jako podproces)."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from gis_assistant_ai import mcp_protocol as proto

BRIDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "gis_assistant_ai", "mcp_bridge.py")


# ------------------------------------------------------------------ HTTP
class TestHttp:
    def test_incomplete_then_complete(self):
        body = b'{"jsonrpc":"2.0","id":1,"method":"ping"}'
        head = b"POST /mcp HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\nAuthorization: Bearer t\r\n\r\n" % len(body)
        assert proto.parse_http_request(head[:20]) is None
        assert proto.parse_http_request(head + body[:5]) is None
        method, path, headers, got, used = proto.parse_http_request(head + body + b"garbage")
        assert (method, path, got) == ("POST", "/mcp", body)
        assert headers["authorization"] == "Bearer t" and used == len(head) + len(body)

    def test_malformed(self):
        with pytest.raises(ValueError):
            proto.parse_http_request(b"nonsense\r\n\r\n")
        with pytest.raises(ValueError):
            proto.parse_http_request(b"POST /mcp HTTP/1.1\r\nContent-Length: 99999999\r\n\r\n")

    def test_response_and_auth(self):
        raw = proto.http_response(200, {"a": "ą"})
        head, body = raw.split(b"\r\n\r\n", 1)
        assert head.startswith(b"HTTP/1.1 200 OK") and b"Content-Length: %d" % len(body) in head
        assert json.loads(body.decode("utf-8")) == {"a": "ą"}
        assert proto.authorized({"authorization": "Bearer abc"}, "abc")
        assert proto.authorized({"x-token": "abc"}, "abc")
        assert not proto.authorized({"authorization": "Bearer abd"}, "abc")
        assert not proto.authorized({}, "abc") and not proto.authorized({"authorization": "Bearer "}, "")


# ------------------------------------------------------------------ JSON-RPC
class TestDispatcher:
    def _dispatch(self, msg, call_tool=None):
        out = []
        d = proto.Dispatcher(call_tool or (lambda n, a, r: r(proto.tool_text("ok"))), "9.9", "instr")
        d.handle(msg, out.append)
        return out[0]

    def test_initialize_and_list(self):
        r = self._dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert r["result"]["protocolVersion"] == proto.PROTOCOL_VERSION
        assert r["result"]["serverInfo"] == {"name": proto.SERVER_NAME, "version": "9.9"}
        r = self._dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in r["result"]["tools"]]
        assert "bdot10k_layer" in names and "run_plan" in names
        assert all("step" not in t for t in r["result"]["tools"])
        assert all("inputSchema" in t and t["description"] for t in r["result"]["tools"])

    def test_notification_and_unknown(self):
        assert self._dispatch({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
        r = self._dispatch({"jsonrpc": "2.0", "id": 3, "method": "nope"})
        assert r["error"]["code"] == proto.METHOD_NOT_FOUND
        r = self._dispatch({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "x"}})
        assert r["error"]["code"] == proto.INVALID_PARAMS
        assert self._dispatch("garbage")["error"]["code"] == proto.INVALID_REQUEST

    def test_tool_call_async(self):
        pending = {}

        def call_tool(name, args, respond):
            pending["respond"] = respond
            pending["name"], pending["args"] = name, args

        out = []
        proto.Dispatcher(call_tool).handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                            "params": {"name": "zoom_to_layer", "arguments": {"layer": "L"}}},
                                           out.append)
        assert out == [] and pending["name"] == "zoom_to_layer"
        pending["respond"](proto.tool_text("done", structured={"x": 1}))
        assert out[0]["id"] == 7 and out[0]["result"]["content"][0]["text"] == "done"
        assert out[0]["result"]["structuredContent"] == {"x": 1}


# ------------------------------------------------------------------ mapowanie narzędzi
class TestToolMapping:
    def test_processing(self):
        step = proto.tool_to_step("run_processing", {"algorithm": "native:buffer",
                                                     "params": {"INPUT": "abc", "DISTANCE": 100},
                                                     "output_name": "Bufor", "selected_only": True})
        assert step["action"] == "processing" and step["algorithm"] == "native:buffer"
        assert step["params"]["INPUT"] == {"source": "abc", "selected_only": True}
        assert step["title"] == "Bufor" and step["output_name"] == "Bufor"

    def test_generic_strips_consent_flag(self):
        step = proto.tool_to_step("load_layer", {"provider": "ogr", "uri": "https://x/y.geojson", "name": "Y",
                                                 "allow_internal_network": True})
        assert step == {"id": "s1", "action": "load_layer", "title": "Y", "provider": "ogr",
                        "uri": "https://x/y.geojson", "name": "Y"}
        assert proto.tool_to_step("bdot10k_layer", {"teryt": "1418", "class": "OT_SKDR_L"})["title"] == "OT_SKDR_L"
        assert proto.tool_to_step("qgis_context", {}) is None

    def test_plan_from_args(self):
        plan = proto.plan_from_args({"steps": [{"action": "uldk_boundary", "level": "powiat", "teryt": "1418"},
                                               {"id": "zz", "action": "zoom", "layer": "{{s1}}"}]})
        assert [s["id"] for s in plan["steps"]] == ["s1", "zz"]
        assert plan["steps"][0]["title"] == "uldk_boundary" and plan["type"] == "plan"

    def test_language(self):
        out = []
        proto.Dispatcher(lambda n, a, r: None, lang="en_GB").handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                                                    out.append)
        descs = [t["description"] for t in out[0]["result"]["tools"]]
        assert descs[0].startswith("Description") and not any("ż" in d or "ą" in d for d in descs)
        assert proto.normalize_lang("pl_PL") == "pl" and proto.normalize_lang("de_DE") == "en"
        assert proto.public_tools("pl")[0]["description"].startswith("Opis")

    def test_claude_config(self):
        cfg = proto.claude_desktop_config("C:/py/pythonw.exe", "C:/p/mcp_bridge.py", "http://127.0.0.1:8765/mcp",
                                          "tok")
        srv = cfg["mcpServers"]["qgis-gis-assistant"]
        assert srv["command"] == "C:/py/pythonw.exe" and srv["args"][1:] == ["--url", "http://127.0.0.1:8765/mcp",
                                                                              "--lang", "pl"]
        assert srv["env"]["GIS_ASSISTANT_MCP_TOKEN"] == "tok"


# ------------------------------------------------------------------ most stdio ↔ HTTP
class _FakeQgis(BaseHTTPRequestHandler):
    """Udaje serwer we wtyczce: wymaga tokenu, odpowiada JSON-RPC, powiadomienia kwituje 202."""
    token = "secret"

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        if self.headers.get("Authorization") != "Bearer " + self.token:
            self._send(401, {"error": "unauthorized"})
            return
        if body.get("id") is None:
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send(200, {"jsonrpc": "2.0", "id": body["id"],
                         "result": {"echo": body["method"], "args": body.get("params")}})

    def _send(self, status, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_qgis():
    srv = HTTPServer(("127.0.0.1", 0), _FakeQgis)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d/mcp" % srv.server_port
    srv.shutdown()


def _run_bridge(url, token, messages, lang="pl"):
    proc = subprocess.run([sys.executable, BRIDGE, "--url", url, "--lang", lang],
                          input="\n".join(json.dumps(m) for m in messages),
                          capture_output=True, text=True, timeout=30, env={**os.environ,
                                                                             "GIS_ASSISTANT_MCP_TOKEN": token})
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()], proc.stderr


class TestBridge:
    def test_relays_requests_and_swallows_notifications(self, fake_qgis):
        out, err = _run_bridge(fake_qgis, "secret", [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"x": 1}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
        assert [o["id"] for o in out] == [1, 2]
        assert out[0]["result"]["echo"] == "initialize" and out[1]["result"]["echo"] == "tools/list"
        assert err == ""

    def test_wrong_token_is_reported_to_claude(self, fake_qgis):
        out, err = _run_bridge(fake_qgis, "wrong", [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "qgis_context", "arguments": {}}}])
        assert out[0]["result"]["isError"] is True and "401" in err
        assert "token" in out[0]["result"]["content"][0]["text"]

    def test_offline_qgis(self):
        out, _ = _run_bridge("http://127.0.0.1:9/mcp", "t", [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "qgis_status"}}])
        assert out[0]["result"]["serverInfo"]["version"] == "offline"
        assert out[1]["result"]["tools"][0]["name"] == "qgis_status"
        assert out[2]["result"]["isError"] and "Uruchom QGIS" in out[2]["result"]["content"][0]["text"]

    def test_offline_qgis_english(self):
        out, _ = _run_bridge("http://127.0.0.1:9/mcp", "t", [
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "qgis_status"}}], lang="en")
        assert out[0]["result"]["tools"][0]["description"].startswith("QGIS is not responding")
        assert "Start QGIS" in out[1]["result"]["content"][0]["text"]
