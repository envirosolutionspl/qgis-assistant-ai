# -*- coding: utf-8 -*-
"""HTML dla panelu wyników.

QTextBrowser obsługuje tylko podzbiór HTML4 – stąd układ na tabelach.
"""
from urllib.parse import urlsplit

from ..i18n import N_, tr
from ..utils import (
    esc, is_web_url, md_to_html, plugin_slug_from_url, short_json,
)

ACTION_LABELS = {
    "processing": N_("PROCESSING"),
    "processing_dialog": N_("OKNO NARZĘDZIA"),
    "load_layer": N_("WCZYTANIE WARSTWY"),
    "add_service": N_("USŁUGA SIECIOWA"),
    "uldk_boundary": "ULDK GUGiK",
    "bdot10k_layer": "BDOT10k GUGiK",
    "user_action": N_("TWOJA AKCJA"),
    "zoom": N_("MAPA"),
    "python": N_("KOD PYQGIS"),
    "note": N_("INFORMACJA"),
}
STATUS_GLYPH = {"pending": "○", "running": "◉", "done": "✔", "error": "✖",
                "waiting": "❚❚", "skipped": "↷"}
# status kroku → klucz palety: kolor znaku statusu i tło wiersza
STATUS_COLOR = {"pending": "muted", "running": "running", "done": "ok",
                "error": "error", "waiting": "warn", "skipped": "muted"}
STATUS_ROW_BG = {"running": "primary_soft", "waiting": "row_wait",
                 "error": "row_error"}


def _wrap(p, body):
    return ("<html><body style='font-family:\"Segoe UI\",\"Noto Sans\","
            "sans-serif;font-size:12px;"
            "color:%s;background:%s;'>%s</body></html>"
            % (p["text"], p["card"], body))


def _md(p, text):
    return md_to_html(text, p["primary"], p["code_bg"])


def _header(p, title, summary=None, kicker=None):
    h = ""
    if kicker:
        h += ("<div style='color:%s;font-size:10px;font-weight:600;"
              "letter-spacing:1px;'>%s</div>" % (p["primary"], esc(kicker)))
    h += ("<div style='font-size:14px;font-weight:600;color:%s;"
          "margin-top:2px;'>%s</div>" % (p["primary_text"], esc(title or "")))
    if summary:
        h += "<div style='color:%s;margin-top:4px;'>%s</div>" % (
            p["text"], _md(p, summary))
    return h


def _badge(p, text, color=None, bg=None):
    return ("<span style='color:%s;background:%s;font-size:9px;"
            "font-weight:600;'>&nbsp;%s&nbsp;</span>"
            % (color or p["primary_text"], bg or p["primary_soft"],
               esc(text).replace(" ", "&nbsp;")))


# ------------------------------------------------------------------ powitanie
def welcome(p, provider_label, model, has_key):
    """Ekran powitalny: jak korzystać z asystenta i stan konfiguracji."""
    rows = [
        (tr("Zapytaj o narzędzie"),
         tr("„Jakim narzędziem połączę kilka warstw w jedną?” – dostaniesz "
            "nazwę, ścieżkę w menu i przycisk otwierający narzędzie.")),
        (tr("Zleć zadanie"),
         tr("„Stwórz bufor 100 m od szkół w powiecie piaseczyńskim” – "
            "dostaniesz plan krok po kroku; kliknij <b>WYKONAJ</b>, "
            "a wtyczka go zrealizuje.")),
        (tr("Współpracuj"),
         tr("Gdy potrzebna będzie Twoja decyzja (np. podłączenie usługi "
            "WMS), plan zatrzyma się i poczeka na potwierdzenie.")),
    ]
    body = _header(p, tr("Witaj w GIS Assistant AI"), None,
                   tr("JAK TO DZIAŁA"))
    body += ("<table cellspacing='0' cellpadding='5' width='100%' "
             "style='margin-top:6px;'>")
    for i, (t, d) in enumerate(rows, 1):
        body += ("<tr><td valign='top' width='22' style='color:%s;"
                 "font-weight:700;font-size:14px;'>%d</td>"
                 "<td><b>%s</b><br><span style='color:%s;'>%s</span></td>"
                 "</tr>" % (p["primary"], i, t, p["muted"], d))
    body += "</table>"
    state = ("<span style='color:%s;'>%s</span>"
             % (p["ok"], tr("✔ gotowy"))) if has_key else (
        "<span style='color:%s;'>⚠</span> <a href='action:settings' "
        "style='color:%s;'>%s</a>"
        % (p["warn"], p["primary"], tr("skonfiguruj klucz API")))
    body += ("<div style='margin-top:8px;color:%s;font-size:11px;'>"
             "%s <b>%s</b> · %s · %s</div>"
             % (p["muted"], tr("Model:"), esc(provider_label), esc(model),
                state))
    return _wrap(p, body)


def thinking(p, query):
    """Ekran oczekiwania na odpowiedź modelu z treścią polecenia."""
    body = _header(p, tr("Analizuję polecenie…"), None,
                   tr("ASYSTENT PRACUJE"))
    body += ("<div style='color:%s;margin-top:6px;font-style:italic;'>"
             "„%s”</div>" % (p["muted"], esc(query)))
    return _wrap(p, body)


def error(p, message, raw=None):
    """Komunikat błędu, opcjonalnie z fragmentem odpowiedzi modelu."""
    body = _header(p, tr("Coś poszło nie tak"), None, tr("BŁĄD"))
    body += "<div style='color:%s;margin-top:6px;'>%s</div>" % (
        p["error"], esc(message).replace("\n", "<br>"))
    if raw:
        body += ("<div style='color:%s;margin-top:8px;font-size:10px;'>"
                 "%s</div>"
                 "<pre style='background:%s;font-size:10px;"
                 "white-space:pre-wrap;'>%s</pre>"
                 % (p["muted"], tr("Fragment odpowiedzi modelu:"),
                    p["code_bg"], esc(raw[:1500])))
    body += ("<div style='margin-top:8px;'><a href='action:retry' "
             "style='color:%s;'>%s</a></div>"
             % (p["primary"], tr("↻ Spróbuj ponownie")))
    return _wrap(p, body)


# ------------------------------------------------------------------ odpowiedzi
def answer(p, resp):
    """Odpowiedź tekstowa modelu (Markdown)."""
    body = _header(p, resp.get("title") or tr("Odpowiedź"), None,
                   tr("ODPOWIEDŹ"))
    body += "<div style='margin-top:6px;'>%s</div>" % _md(
        p, resp.get("text", ""))
    return _wrap(p, body)


def clarify(p, resp):
    """Pytanie doprecyzowujące; opcje to linki action:answer:<numer>."""
    body = _header(p, resp.get("title") or tr("Potrzebuję doprecyzowania"),
                   None, tr("PYTANIE"))
    body += "<div style='margin-top:6px;'>%s</div>" % _md(
        p, resp.get("question", ""))
    opts = resp.get("options") or []
    if opts:
        body += "<div style='margin-top:8px;'>"
        # numer opcji – dock odczyta jej treść z response["options"]
        for i, o in enumerate(opts[:6]):
            body += ("<a href='action:answer:%d' style='color:%s;'>› %s</a>"
                     "<br>" % (i, p["primary"], esc(o)))
        body += "</div>"
    body += ("<div style='color:%s;margin-top:6px;font-size:11px;'>%s</div>"
             % (p["muted"], tr("Odpowiedz w polu poleceń lub kliknij opcję.")))
    return _wrap(p, body)


def tools(p, resp, installed_plugins):
    """Proponowane narzędzia: ścieżki w menu i linki do ich otwarcia."""
    body = _header(p, resp.get("title") or tr("Proponowane narzędzie"),
                   resp.get("summary"), tr("NARZĘDZIE"))
    for t in resp.get("tools", []):
        name = t.get("name") or t.get("name_en") or tr("Narzędzie")
        en = t.get("name_en")
        body += ("<table width='100%%' cellspacing='0' cellpadding='8' "
                 "style='margin-top:8px;"
                 "background:%s;border:1px solid %s;'><tr><td>"
                 % (p["panel"], p["border"]))
        body += ("<span style='font-size:13px;font-weight:600;'>%s</span>"
                 % esc(name))
        if en and en != name:
            body += " <span style='color:%s;'>(%s)</span>" % (p["muted"],
                                                              esc(en))
        kind = {"plugin": tr("WTYCZKA"), "menu": tr("MENU"),
                "algorithm": tr("ALGORYTM")}.get(t.get("kind"), "")
        if kind:
            body += "&nbsp;&nbsp;" + _badge(p, kind)
        for label, key in ((tr("Menu"), "menu_path"),
                           (tr("Przybornik"), "toolbox_path")):
            if t.get(key):
                body += ("<div style='margin-top:5px;'><span style='color:%s;"
                         "font-size:10px;'>%s:</span> "
                         "<b style='color:%s;'>%s</b></div>" % (
                             p["muted"], label, p["primary_text"],
                             esc(t[key]).replace("&gt;", "›")))
        if t.get("description"):
            body += "<div style='margin-top:5px;'>%s</div>" % _md(
                p, t["description"])
        links = []
        if t.get("algorithm_id"):
            links.append("<a href='action:open_alg:%s' style='color:%s;"
                         "font-weight:600;'>%s</a>"
                         "&nbsp;<span style='color:%s;"
                         "font-family:Consolas,monospace;font-size:10px;'>"
                         "%s</span>"
                         % (esc(t["algorithm_id"]), p["primary"],
                            tr("▶ Otwórz narzędzie"), p["muted"],
                            esc(t["algorithm_id"])))
        if t.get("dsm_page"):
            links.append("<a href='action:dsm:%s' style='color:%s;"
                         "font-weight:600;'>%s</a>"
                         % (esc(t["dsm_page"]), p["primary"],
                            tr("▶ Menedżer źródeł danych")))
        if is_web_url(t.get("plugin_url")):  # tylko http(s)
            slug = plugin_slug_from_url(t["plugin_url"])
            links.append("<a href='%s' style='color:%s;font-weight:600;'>"
                         "%s</a>" % (esc(t["plugin_url"]), p["primary"],
                                     tr("↗ Strona wtyczki")))
            if slug and slug in installed_plugins:
                links.append("<span style='color:%s;'>%s</span>"
                             % (p["ok"], tr("✔ zainstalowana")))
            else:
                links.append("<a href='action:plugin_manager' "
                             "style='color:%s;'>%s</a>"
                             % (p["primary"],
                                tr("Zainstaluj w Menedżerze wtyczek")))
        if t.get("_warning"):
            links.append("<span style='color:%s;'>⚠</span> %s"
                         % (p["warn"], esc(t["_warning"])))
        if links:
            body += "<div style='margin-top:7px;'>%s</div>" % (
                " &nbsp;·&nbsp; ".join(links))
        body += "</td></tr></table>"
    return _wrap(p, body)


# ------------------------------------------------------------------ plan
def plan(p, resp, show_details=False, note=None):
    """Plan działań: tabela kroków ze statusem wykonania."""
    kicker = _plan_kicker(len(resp.get("steps", [])))
    body = _header(p, resp.get("title") or tr("Plan działań"),
                   resp.get("summary"), kicker)
    if resp.get("assumptions"):
        body += ("<div style='color:%s;font-size:11px;margin-top:4px;'>"
                 "%s %s</div>"
                 % (p["muted"], tr("Założenia:"),
                    esc("; ".join(str(a) for a in resp["assumptions"]))))
    if note:
        body += ("<div style='color:%s;font-size:11px;margin-top:4px;'>"
                 "<span style='color:%s;'>↻</span> %s</div>"
                 % (p["muted"], p["running"], esc(note)))
    body += ("<table width='100%' cellspacing='0' cellpadding='6' "
             "style='margin-top:8px;'>")
    for n, s in enumerate(resp.get("steps", []), 1):
        body += _step_row(p, n, s, show_details)
    body += "</table>"
    if resp.get("result_description"):
        body += ("<div style='margin-top:6px;color:%s;'><b>%s</b> %s</div>"
                 % (p["muted"], tr("Rezultat:"),
                    esc(resp["result_description"])))
    return _wrap(p, body)


def _step_row(p, n, s, show_details):
    status = s.get("_status", "pending")
    color = p[STATUS_COLOR[status]]
    bg = p[STATUS_ROW_BG.get(status, "card")]
    glyph = STATUS_GLYPH[status]
    title_style = "font-weight:600;" + (
        "text-decoration:line-through;color:%s;" % p["muted"]
        if status == "skipped" else "")
    row = ("<tr style='background:%s;'><td valign='top' width='34' "
           "align='center' style='border-bottom:1px solid %s;'>"
           "<span style='color:%s;font-size:14px;font-weight:700;'>%s</span>"
           "<br>"
           "<span style='color:%s;font-size:10px;'>%d</span></td>"
           "<td valign='top' style='border-bottom:1px solid %s;'>" % (
               bg, p["border"], color, glyph, p["muted"], n, p["border"]))
    label = tr(ACTION_LABELS.get(s["action"], s["action"].upper()))
    if s["action"] in ("user_action", "python"):
        badge = _badge(p, label, p["warn_text"], p["warn_bg"])
    else:
        badge = _badge(p, label)
    row += "<span style='%s'>%s</span>&nbsp;&nbsp;%s" % (
        title_style, esc(s["title"]), badge)
    if s.get("description"):
        row += "<div style='color:%s;margin-top:2px;'>%s</div>" % (
            p["muted"], esc(s["description"]))
    elif s["action"] == "user_action" and s.get("message"):
        row += "<div style='color:%s;margin-top:2px;'>%s</div>" % (
            p["muted"], _md(p, str(s["message"])[:400]))
    meta = _meta(s)
    if meta:
        row += ("<div style='color:%s;font-size:10px;"
                "font-family:Consolas,monospace;margin-top:2px;'>%s</div>"
                % (p["primary_text"], esc(meta)))
    if show_details:
        details = {k: v for k, v in s.items()
                   if not k.startswith("_") and k not in (
                       "id", "action", "title", "description", "message")}
        row += ("<div style='color:%s;font-size:10px;"
                "font-family:Consolas,monospace;margin-top:2px;'>%s</div>"
                % (p["muted"], esc(short_json(details, 700))))
    if s.get("_result_text"):
        row += ("<div style='color:%s;font-size:11px;margin-top:3px;'>"
                "→ %s</div>" % (p["ok"], esc(s["_result_text"])))
    if s.get("_warning"):
        row += ("<div style='color:%s;font-size:11px;margin-top:3px;'>"
                "⚠ %s</div>" % (p["warn"], esc(s["_warning"][:600])))
    if s.get("_error"):
        row += ("<div style='color:%s;font-size:11px;margin-top:3px;'>"
                "%s</div>"
                % (p["error"], esc(s["_error"][:600]).replace("\n", "<br>")))
    for w in s.get("_warnings", []):
        row += ("<div style='font-size:11px;margin-top:2px;'>"
                "<span style='color:%s;'>⚠</span> %s</div>"
                % (p["warn"], esc(w)))
    row += "</td></tr>"
    return row


def _meta(s):
    a = s["action"]
    if a in ("processing", "processing_dialog"):
        return s.get("algorithm", "")
    if a == "load_layer":
        return "%s · %s" % ((s.get("provider") or "").upper(),
                            s.get("name") or "")
    if a == "add_service":
        host = urlsplit(str(s.get("url") or "")).netloc
        return "%s · %s · %s" % ((s.get("service_type") or "").upper(), host,
                                 ", ".join(s.get("layers") or []))
    if a == "uldk_boundary":
        t = s.get("teryt")
        return "%s · TERYT %s" % (s.get("level", ""),
                                  ", ".join(t) if isinstance(t, list) else t)
    if a == "bdot10k_layer":
        return "%s · %s %s" % (s.get("class") or "", tr("powiat"),
                               s.get("teryt") or "")
    return ""


def _plan_kicker(n):
    """Polska odmiana liczebnika; tłumaczenia mapują każdą formę na własną."""
    if n == 1:
        return tr("PLAN DZIAŁAŃ · %d KROK") % n
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return tr("PLAN DZIAŁAŃ · %d KROKI") % n
    return tr("PLAN DZIAŁAŃ · %d KROKÓW") % n
