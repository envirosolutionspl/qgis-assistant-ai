#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Most MCP stdio ↔ HTTP dla wtyczki GIS Assistant AI (QGIS).

Claude Desktop uruchamia ten skrypt jako lokalny serwer MCP (transport stdio)
i rozmawia z nim JSON-RPC po jednej linii na komunikat. Skrypt przekazuje
każde żądanie do serwera działającego wewnątrz QGIS
(POST http://127.0.0.1:PORT/mcp, token w nagłówku) i odsyła odpowiedź. Nie
importuje QGIS ani bibliotek spoza standardowej biblioteki Pythona – działa
z dowolnym Pythonem 3.8+.

Gdy QGIS nie jest uruchomiony (albo serwer we wtyczce jest wyłączony), most
odpowiada sam na „initialize”, a w „tools/list” zwraca jedno narzędzie
z instrukcją, jak włączyć serwer – Claude nie zobaczy błędu połączenia, tylko
czytelny komunikat.

Użycie:
    mcp_bridge.py --url http://127.0.0.1:8765/mcp [--token TOKEN]
                  [--lang pl|en]

Token można też podać w zmiennej środowiskowej GIS_ASSISTANT_MCP_TOKEN; język
komunikatów jest zgodny z interfejsem QGIS.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# musi być zgodna z mcp_protocol (most nie importuje wtyczki – sprawdza to
# test)
PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "gis-assistant-ai-qgis"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
CALL_TIMEOUT_S = 21 * 60        # dłużej niż limit narzędzia w QGIS (20 min)
OTHER_TIMEOUT_S = 30

TEXTS = {
    "pl": {
        "tool": "QGIS nie odpowiada. Wywołaj, aby zobaczyć, jak połączyć się "
                "z wtyczką GIS Assistant AI w QGIS.",
        "instructions": "QGIS nie jest w tej chwili dostępny. Wywołaj "
                        "qgis_status, aby zobaczyć instrukcję.",
        "offline": (
            "Nie można połączyć się z QGIS pod adresem %s. Uruchom QGIS, "
            "włącz wtyczkę GIS Assistant AI i w jej ustawieniach zaznacz "
            "„Serwer MCP (Claude Desktop)”. Jeśli serwer jest włączony, "
            "sprawdź port i token w konfiguracji Claude Desktop (przycisk "
            "„Skopiuj konfigurację Claude Desktop” w ustawieniach "
            "wtyczki).\nSzczegóły: %s"),
        "token": "serwer odrzucił token (401) – odśwież konfigurację Claude "
                 "Desktop z ustawień wtyczki",
    },
    "en": {
        "tool": "QGIS is not responding. Call to see how to connect to the "
                "GIS Assistant AI plugin in QGIS.",
        "instructions": "QGIS is currently unavailable. Call qgis_status to "
                        "see the instructions.",
        "offline": (
            "Cannot connect to QGIS at %s. Start QGIS, enable the GIS "
            "Assistant AI plugin and tick “MCP server (Claude Desktop)” in "
            "its settings. If the server is enabled, check the port and token "
            "in the Claude Desktop configuration (button “Copy Claude Desktop "
            "configuration” in the plugin settings).\nDetails: %s"),
        "token": "the server rejected the token (401) – refresh the Claude "
                 "Desktop configuration from the plugin settings",
    },
}
LANG = "pl"


def _t(key):
    return TEXTS.get(LANG, TEXTS["en"])[key]


def _offline_tool():
    return {"name": "qgis_status", "description": _t("tool"),
            "inputSchema": {"type": "object", "properties": {},
                            "additionalProperties": False}}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Bez przekierowań – nagłówek z tokenem nie może trafić pod inny adres."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Odrzuć przekierowanie (urllib zgłosi wtedy HTTPError 3xx)."""
        return None


# Bez ProxyHandler({}) urllib użyłby proxy systemowego (HTTP_PROXY, ustawienia
# Windows) i token mógłby trafić do serwera proxy; serwer w QGIS jest zawsze
# lokalny.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                      _NoRedirect)


def local_url(url):
    """Czy adres wskazuje serwer lokalny po http.

    Tylko taki serwer uruchamia wtyczka.
    """
    try:
        parts = urllib.parse.urlsplit(url)
        # .port zgłasza ValueError dla nieprawidłowego portu
        host, _ = parts.hostname, parts.port
    except ValueError:
        return False
    return parts.scheme == "http" and host in LOCAL_HOSTS


def _post(url, token, message, timeout):
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "Authorization": "Bearer %s" % token,
        "User-Agent": "gis-assistant-mcp-bridge"})
    # Bandit B310: schemat i host sprawdzone w main() (local_url: tylko
    # http://127.0.0.1 / localhost)
    with _OPENER.open(req, timeout=timeout) as resp:  # nosec B310
        body = resp.read()
        if resp.status == 202 or not body:
            return None
        return json.loads(body.decode("utf-8"))


def _reply(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error_text(exc):
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            detail = ""
        if exc.code == 401:
            return _t("token")
        return "HTTP %d %s" % (exc.code, detail)
    return str(exc)


def _offline_response(message, detail, url):
    """Odpowiedź generowana lokalnie, gdy QGIS nie odpowiada.

    detail – opis błędu z _error_text().
    """
    msg_id, method = message.get("id"), message.get("method")
    if msg_id is None:
        return None
    if method == "initialize":
        # listChanged: po połączeniu z QGIS most wyśle
        # notifications/tools/list_changed (zob. main)
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": SERVER_NAME, "version": "offline"},
            "instructions": _t("instructions")}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": [_offline_tool()]}}
    if method == "tools/call":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "content": [{"type": "text",
                         "text": _t("offline") % (url, detail)}],
            "isError": True}}
    if method in ("resources/list", "prompts/list"):
        return {"jsonrpc": "2.0", "id": msg_id,
                "result": {"resources": [], "prompts": []}}
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32000,
                      "message": "QGIS unavailable: %s" % detail}}


def _http_error_response(message, status, detail):
    """Błąd JSON-RPC z kodem statusu HTTP, którym odpowiedział QGIS.

    QGIS działa, ale zwrócił błąd HTTP (np. 400, 404) – to nie jest sytuacja
    „QGIS offline”.
    """
    msg_id = message.get("id")
    if msg_id is None:
        return None
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32000, "message": "QGIS: %s" % detail,
                      "data": {"httpStatus": status}}}


def main():
    """Przekazuj komunikaty ze stdin do QGIS i odpowiedzi na stdout."""
    ap = argparse.ArgumentParser(
        description="MCP stdio bridge for GIS Assistant AI (QGIS)")
    ap.add_argument("--url", default=os.environ.get(
        "GIS_ASSISTANT_MCP_URL", "http://127.0.0.1:8765/mcp"))
    ap.add_argument("--token",
                    default=os.environ.get("GIS_ASSISTANT_MCP_TOKEN", ""))
    ap.add_argument("--lang",
                    default=os.environ.get("GIS_ASSISTANT_MCP_LANG", "pl"),
                    help="language of bridge messages: pl or en (follows the "
                         "QGIS interface language)")
    args = ap.parse_args()
    global LANG
    LANG = "pl" if args.lang.lower().startswith("pl") else "en"
    if not local_url(args.url):
        ap.error("--url must point to the local QGIS server "
                 "(http://127.0.0.1:PORT/mcp or http://localhost:PORT/mcp)")
    if not args.token:
        sys.stderr.write("mcp_bridge: missing token (--token or "
                         "GIS_ASSISTANT_MCP_TOKEN)\n")
    # Windows: stdout w trybie tekstowym zamienia \n na \r\n – MCP tego nie
    # lubi
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    # most sam odpowiedział na initialize (listChanged: True)
    advertised = False
    # Claude dostał odpowiedź „offline” – po połączeniu lista narzędzi się
    # zmieni
    stale = False
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            _reply({"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "Parse error"}})
            continue
        if not isinstance(message, dict):
            _reply({"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600,
                              "message": "batch not supported"}})
            continue
        timeout = (CALL_TIMEOUT_S if message.get("method") == "tools/call"
                   else OTHER_TIMEOUT_S)
        online = False
        try:
            response = _post(args.url, args.token, message, timeout)
            online = True
        except urllib.error.HTTPError as exc:
            detail = _error_text(exc)
            sys.stderr.write("mcp_bridge: %s\n" % detail)
            # zły token – czytelna instrukcja jak przy braku połączenia
            if exc.code == 401:
                response = _offline_response(message, detail, args.url)
            else:
                response = _http_error_response(message, exc.code, detail)
                online = True
        # każdy błąd połączenia obsługujemy komunikatem dla Claude
        except Exception as exc:  # noqa: BLE001
            detail = _error_text(exc)
            sys.stderr.write("mcp_bridge: %s\n" % detail)
            response = _offline_response(message, detail, args.url)
        if not online:
            stale = True
            advertised = advertised or message.get("method") == "initialize"
        if response is not None:
            _reply(response)
        if online and stale and advertised:
            _reply({"jsonrpc": "2.0",
                    "method": "notifications/tools/list_changed"})
            stale = False


if __name__ == "__main__":
    main()
