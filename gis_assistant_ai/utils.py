# -*- coding: utf-8 -*-
"""Funkcje pomocnicze niezależne od QGIS (łatwe do testowania)."""
import html
import json
import os
import re
from .i18n import N_, tr


# ---------------------------------------------------- JSON z odpowiedzi modelu

def extract_json(text):
    """Wyciągnij pierwszy poprawny obiekt JSON z odpowiedzi modelu.

    Najpierw sprawdza blok ```json```, potem cały tekst; zgłasza ValueError,
    gdy obiektu nie ma.
    """
    if not text or not text.strip():
        raise ValueError(tr("Model zwrócił pustą odpowiedź."))
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.S | re.I)
    candidates = [fence.group(1).strip()] if fence else []
    candidates.append(t)
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        obj = _scan_object(cand)
        if obj is not None:
            return obj
    raise ValueError(tr("Nie udało się odczytać odpowiedzi modelu jako "
                        "JSON."))


def _scan_object(t):
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(t[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except ValueError:
                        pass
                    # obiekt zamknięty, ale niepoprawny – szukamy od
                    # kolejnego „{”
                    break
        start = t.find("{", start + 1)
    return None


# ----------------------------------------------------------- usuwanie sekretów

_SECRET = (r"(?:password|passwd|pwd|user|username|login|token|access_token|"
           r"refresh_token|api[_-]?key|apikey|key|secret|client_secret|"
           r"signature|sig|authcfg|sessionid|session)")
LOCAL_PROVIDERS = {"ogr", "gdal", "spatialite", "delimitedtext", "mdal",
                   "pdal", "virtual"}


def sanitize_source(src, provider=""):
    """Usuń hasła, tokeny, loginy i pełne ścieżki dyskowe ze źródła warstwy.

    Wynik trafia do kontekstu wysyłanego do modelu AI – nie może zawierać
    sekretów. Jest skracany do 300 znaków.
    """
    if not src:
        return ""
    s = str(src)
    # user:haslo@host w adresach URL
    s = re.sub(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/\s@'\"]*@", r"\1***@", s)
    # klucz='wartość' / klucz="wartość"
    s = re.sub(r"(?i)\b(%s)\s*=\s*'[^']*'" % _SECRET, r"\1='***'", s)
    s = re.sub(r'(?i)\b(%s)\s*=\s*"[^"]*"' % _SECRET, r'\1="***"', s)
    # klucz=wartość (bez cudzysłowów) w query stringach i łańcuchach połączeń
    s = re.sub(r"(?i)(^|[?&;\s|,])(%s)=(?!['\"]|\*\*\*)[^&;\s|,]*" % _SECRET,
               r"\1\2=***", s)
    if (provider or "").lower() in LOCAL_PROVIDERS:
        s = _strip_local_path(s)
    return s[:300]


def _strip_local_path(s):
    m = re.match(r"^(?P<prefix>file://)?"
                 r"(?P<path>(?:/?[A-Za-z]:)?[\\/][^|?]*)(?P<rest>.*)$",
                 s, re.S)
    if not m:
        return s
    path = m.group("path").replace("\\", "/")
    return os.path.basename(path.rstrip("/")) + m.group("rest")


def redact_key(text, secret):
    """Zwróć tekst z kluczem zastąpionym przez „***” (komunikaty, logi)."""
    if secret and text:
        return str(text).replace(secret, "***")
    return text


# ---------------------------------------------------- referencje {{s1.OUTPUT}}

REF_RE = re.compile(r"\{\{\s*([A-Za-z0-9_\-]+)(?:\.([A-Za-z0-9_]+))?\s*\}\}")


def resolve_refs(value, lookup):
    """Podmień {{id}} / {{id.KLUCZ}} na wyniki wcześniejszych kroków.

    Jeżeli cały napis jest referencją, zwracana jest wartość (dowolnego
    typu), w przeciwnym razie referencje są wstawiane jako tekst. Słowniki
    i listy są przetwarzane rekurencyjnie; lookup(id, klucz) dostarcza
    wartość.
    """
    if isinstance(value, dict):
        return {k: resolve_refs(v, lookup) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_refs(v, lookup) for v in value]
    if isinstance(value, str):
        m = REF_RE.fullmatch(value.strip())
        if m:
            return lookup(m.group(1), m.group(2))
        return REF_RE.sub(lambda mm: str(lookup(mm.group(1), mm.group(2))),
                          value)
    return value


def find_refs(value):
    """Zwróć zbiór id kroków, do których odwołuje się wartość ({{id…}})."""
    found = set()
    if isinstance(value, dict):
        for v in value.values():
            found |= find_refs(v)
    elif isinstance(value, list):
        for v in value:
            found |= find_refs(v)
    elif isinstance(value, str):
        found |= {m.group(1) for m in REF_RE.finditer(value)}
    return found


# ------------------------------------------------------- mini markdown -> HTML

def esc(text):
    """Zwróć tekst bezpieczny w HTML (także w atrybutach); None → ""."""
    return html.escape(str(text if text is not None else ""), quote=True)


_URL_RE = re.compile(r"(https?://[^\s<>\"')]+)")


def md_to_html(text, link_color="#4c6e4f", code_bg="#eef3ee"):
    """Zamień prosty Markdown na HTML.

    Obsługuje akapity, listy, **pogrubienie**, `kod` i linki; reszta tekstu
    jest escapowana.
    """
    if not text:
        return ""
    out, in_list = [], False
    for raw in str(text).splitlines():
        line = raw.rstrip()
        bullet = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)$", line)
        if bullet:
            if not in_list:
                out.append("<ul style='margin-top:2px;margin-bottom:2px;'>")
                in_list = True
            out.append("<li>%s</li>"
                       % _inline(bullet.group(1), link_color, code_bg))
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if not line.strip():
            out.append("<div style='height:6px'></div>")
        else:
            out.append("<div>%s</div>" % _inline(line, link_color, code_bg))
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _inline(s, link_color, code_bg):
    links = {}

    def keep_md_link(m):
        key = "\x00%d\x00" % len(links)
        links[key] = "<a href='%s' style='color:%s'>%s</a>" % (
            esc(m.group(2)), link_color, esc(m.group(1)))
        return key

    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", keep_md_link, s)

    def keep_url(m):
        key = "\x00%d\x00" % len(links)
        links[key] = "<a href='%s' style='color:%s'>%s</a>" % (
            esc(m.group(1)), link_color, esc(m.group(1)))
        return key

    s = _URL_RE.sub(keep_url, s)
    s = esc(s)
    s = re.sub(r"`([^`]+)`",
               r"<code style='background:%s;"
               r"font-family:Consolas,monospace;'>\1</code>" % code_bg, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    for key, val in links.items():
        s = s.replace(key, val)   # esc() nie zmienia znaczników „\x00n\x00”
    return s


def plugin_slug_from_url(url):
    """Zwróć nazwę wtyczki z adresu plugins.qgis.org/plugins/… albo ""."""
    m = re.search(r"plugins\.qgis\.org/plugins/([^/?#]+)", url or "")
    return m.group(1) if m else ""


def short_json(obj, limit=600):
    """Zwróć JSON obiektu (albo str) skrócony do limit znaków z „…”."""
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "…"


def public_fields(step):
    """Zwróć pola kroku bez wewnętrznych (``_status``, ``_error``…).

    Wynik trafia do promptu i do MCP.
    """
    return {k: v for k, v in step.items() if not k.startswith("_")}


# Konstrukcje kodu Python o skutkach poza projektem QGIS (pliki, procesy,
# sieć, sekrety).
_PY_RISKS = [
    (r"\bimport\s+os\b|\bfrom\s+os\b"
     r"|\bos\.(system|remove|unlink|rmdir|popen|environ|walk|listdir)",
     N_("system operacyjny (os)")),
    (r"\bsubprocess\b|\bpty\b|\bctypes\b", N_("uruchamianie programów")),
    (r"\bshutil\b|\brmtree\b|\bpathlib\b", N_("operacje na plikach")),
    (r"(?<![\w.])open\s*\(", N_("odczyt/zapis plików (open)")),
    (r"\bsocket\b|\burllib\b|\brequests\b|\bhttp\.client\b|\bftplib\b"
     r"|\bsmtplib\b|QNetwork", N_("połączenia sieciowe")),
    (r"\beval\s*\(|\bexec\s*\(|\bcompile\s*\(|__import__|\bimportlib\b",
     N_("dynamiczne wykonanie kodu")),
    (r"QgsAuthManager|authManager\s*\(|\bauthcfg\b|QgsSettings|QSettings",
     N_("uwierzytelnianie i ustawienia QGIS")),
    (r"\bsys\.modules\b|__builtins__|__subclasses__|__globals__",
     N_("introspekcja interpretera")),
    (r"\.deleteLater\s*\(|removeMapLayer|\.clear\s*\(\s*\)|deleteFeatures"
     r"|truncate", N_("usuwanie danych")),
]


def python_risks(code):
    """Zwróć kategorie ryzykownych konstrukcji znalezionych w kodzie.

    To proste wyszukiwanie wzorców (_PY_RISKS), bez analizy składni.
    """
    found = []
    for pattern, label in _PY_RISKS:
        if re.search(pattern, code or "") and label not in found:
            found.append(label)
    return found


def is_web_url(url):
    """Sprawdź, czy adres to http(s).

    Inne schematy (file:, smb:, ms-settings: …) mogą uruchamiać programy
    (audyt A4).
    """
    return bool(re.match(r"(?i)^https?://[^\s/$.?#][^\s]*$",
                         str(url or "").strip()))
