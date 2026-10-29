# -*- coding: utf-8 -*-
"""Usługi sieciowe i dane spod adresu dla kroków wykonywanych samodzielnie przez asystenta.

Logika przeniesiona z Asystenta AI geoportalu MAIP (agent_steps.py, services.py, security.py):
- odczyt GetCapabilities (WMS, WMTS, WFS, WCS) i dobór warstwy po nazwie albo słowach z tytułu,
- dane spod adresu http(s) (GeoJSON, ZIP, GPKG, KML, GML, Overpass API),
- rozpoznanie adresów w sieci wewnętrznej (wczytanie z nich wymaga zgody użytkownika).

Moduł nie zależy od QGIS – zapytania sieciowe wykonuje executor.py (QgsNetworkAccessManager).
"""
import ipaddress
import math
import os
import re
import socket
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .i18n import tr
from .utils import sanitize_source

TYPES = ("wms", "wmts", "wfs", "wcs")
MAX_LAYERS_PER_STEP = 5
_PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


class ServiceError(Exception):
    pass


# ------------------------------------------------------------------ adresy

def base_url(url):
    """Adres usługi bez parametrów SERVICE/REQUEST/VERSION (inne parametry, np. map=…, zostają)."""
    url = str(url or "").strip()
    if not re.match(r"(?i)^https?://", url):
        raise ServiceError(tr("Adres usługi musi zaczynać się od http:// lub https://."))
    p = urlsplit(url)
    keep = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
            if k.upper() not in ("SERVICE", "REQUEST", "VERSION")]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(keep), ""))


def with_params(url, params):
    p = urlsplit(url)
    q = parse_qsl(p.query, keep_blank_values=True) + list(params.items())
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))


def capabilities_url(kind, url):
    params = {"SERVICE": kind.upper(), "REQUEST": "GetCapabilities"}
    if kind == "wcs":
        params["VERSION"] = "1.0.0"
    return with_params(base_url(url), params)


_PRIVATE_SUFFIXES = (".local", ".lan", ".internal", ".localdomain", ".home", ".corp", ".localhost")


def ips_private(ips):
    """True, gdy którykolwiek adres IP należy do sieci wewnętrznej, pętli zwrotnej lub zakresu specjalnego."""
    return any(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
               or ip.is_unspecified for ip in ips)


def private_url_static(url):
    """Ocena adresu BEZ odpytywania DNS: True/False, albo None, gdy nazwę hosta trzeba dopiero rozwiązać.

    Rozwiązywanie nazw wykonuje executor asynchronicznie (QHostInfo), żeby nie blokować interfejsu QGIS.
    """
    host = (urlsplit(str(url or "")).hostname or "").strip().lower()
    if not host:
        return True
    if host == "localhost" or host.endswith(_PRIVATE_SUFFIXES):
        return True
    try:
        return ips_private([ipaddress.ip_address(host)])
    except ValueError:
        return None


def is_private_url(url):
    """True, gdy adres wskazuje na komputer lokalny lub sieć wewnętrzną (albo nazwy nie da się ustalić).

    Adresy wskazane przez model mogą pochodzić z ukrytego polecenia w nazwie warstwy (prompt injection) –
    dane z sieci wewnętrznej trafiłyby potem do opisu projektu wysyłanego do AI. Takie wczytanie wymaga zgody.
    UWAGA: dla nazw hostów wykonuje blokujące zapytanie DNS – w kodzie wtyczki używaj private_url_static()
    + asynchronicznego rozwiązywania (PlanExecutor._require_consent). Ta funkcja zostaje dla testów i skryptów.
    """
    verdict = private_url_static(url)
    if verdict is not None:
        return verdict
    host = (urlsplit(str(url or "")).hostname or "").strip().lower()
    try:
        ips = [ipaddress.ip_address(i[4][0].split("%")[0]) for i in socket.getaddrinfo(host, None)]
    except (OSError, ValueError):
        return True
    return ips_private(ips)


_URI_URL_RE = re.compile(r"""(?i)(?:^|[&\s;|,'"])url=['"]?(https?://[^'"&\s|]+)""")


def redact_url(url):
    """Adres do dziennika – bez haseł, tokenów i kluczy w parametrach (np. ?key=…)."""
    return sanitize_source(url)


def uri_http_url(uri):
    """Adres http(s) zaszyty w URI warstwy QGIS (WMS/WMTS/XYZ: „url=…”, WFS: „url='…'”) albo w zwykłym URL."""
    uri = str(uri or "").strip()
    if re.match(r"(?i)^https?://", uri):
        return uri.split("|", 1)[0]
    m = _URI_URL_RE.search(uri)
    return m.group(1) if m else None


# ------------------------------------------------------------------ XML

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    if el is None:
        return None
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _children(el, name):
    return [c for c in el if _local(c.tag) == name] if el is not None else []


def _text(el, name, default=""):
    c = _child(el, name)
    return (c.text or "").strip() if c is not None and c.text else default


def _iter(el, name):
    return [e for e in el.iter() if _local(e.tag) == name] if el is not None else []


def epsg(code):
    """„urn:ogc:def:crs:EPSG::2180”, „EPSG:2180”, „http://…/EPSG/0/2180” → „EPSG:2180”."""
    m = re.search(r"EPSG(?:/0/|:+)(\d+)", code or "", re.I)
    return "EPSG:%s" % m.group(1) if m else (code or "").strip()


def _exception(root):
    if _local(root.tag) in ("ServiceExceptionReport", "ExceptionReport"):
        msg = " ".join(t.strip() for t in root.itertext() if t.strip())[:300]
        raise ServiceError(tr("Usługa zgłosiła błąd: %s") % (msg or "-"))


def scale_to_zoom(scale):
    return max(0, min(22, math.log2(559082264.029 / scale))) if scale and scale > 0 else None


def parse_wms(root):
    get_map = next(iter(_iter(root, "GetMap")), None)
    formats = [(f.text or "").strip() for f in _iter(get_map, "Format")]
    layers = []

    def geo_bbox(el, inherited):
        ex = _child(el, "EX_GeographicBoundingBox")
        try:
            if ex is not None:
                return [float(_text(ex, "westBoundLongitude")), float(_text(ex, "southBoundLatitude")),
                        float(_text(ex, "eastBoundLongitude")), float(_text(ex, "northBoundLatitude"))]
            ll = _child(el, "LatLonBoundingBox")
            if ll is not None:
                return [float(ll.get("minx")), float(ll.get("miny")), float(ll.get("maxx")), float(ll.get("maxy"))]
        except (TypeError, ValueError):
            pass
        return inherited

    def walk(el, crs, bbox=None):
        bbox = geo_bbox(el, bbox)
        crs = crs + [epsg((c.text or "").strip()) for c in _children(el, "CRS") + _children(el, "SRS")]
        name = _text(el, "Name")
        if name:
            layers.append({"name": name, "title": _text(el, "Title") or name, "crs": sorted(set(crs)), "bbox": bbox})
        for sub in _children(el, "Layer"):
            walk(sub, crs, bbox)

    for top in _children(_child(root, "Capability"), "Layer"):
        walk(top, [])
    return {"version": root.get("version", "1.3.0"), "formats": formats, "layers": layers}


def parse_wmts(root):
    contents = _child(root, "Contents")
    if contents is None:
        raise ServiceError(tr("To nie wygląda na usługę WMTS (brak sekcji Contents)."))
    sets = {_text(ts, "Identifier"): epsg(_text(ts, "SupportedCRS")) for ts in _children(contents, "TileMatrixSet")}
    layers = []
    for ly in _children(contents, "Layer"):
        links = [_text(lk, "TileMatrixSet") for lk in _children(ly, "TileMatrixSetLink")]
        styles = _children(ly, "Style")
        default = next((s for s in styles if (s.get("isDefault") or "").lower() == "true"),
                       styles[0] if styles else None)
        bbox = None
        wgs = _child(ly, "WGS84BoundingBox")
        if wgs is not None:
            try:
                lo = [float(v) for v in _text(wgs, "LowerCorner").split()]
                hi = [float(v) for v in _text(wgs, "UpperCorner").split()]
                bbox = [lo[0], lo[1], hi[0], hi[1]]
            except (ValueError, IndexError):
                bbox = None
        layers.append({"name": _text(ly, "Identifier"), "title": _text(ly, "Title") or _text(ly, "Identifier"),
                       "matrix_sets": [{"id": s, "crs": sets.get(s, "")} for s in links if s],
                       "formats": [(f.text or "").strip() for f in _children(ly, "Format")],
                       "style": _text(default, "Identifier") if default is not None else "default", "bbox": bbox})
    return {"version": root.get("version", "1.0.0"), "layers": layers}


def parse_wfs(root):
    layers = []
    for ft in _children(_child(root, "FeatureTypeList"), "FeatureType"):
        crs = [epsg(_text(ft, n)) for n in ("DefaultCRS", "DefaultSRS", "SRS") if _text(ft, n)]
        crs += [epsg((e.text or "").strip()) for e in _children(ft, "OtherCRS") + _children(ft, "OtherSRS")]
        layers.append({"name": _text(ft, "Name"), "title": _text(ft, "Title") or _text(ft, "Name"),
                       "crs": list(dict.fromkeys(crs))})
    return {"version": root.get("version", ""), "layers": layers}


def parse_wcs(root):
    layers = []
    for c in _iter(root, "CoverageOfferingBrief"):                     # WCS 1.0
        layers.append({"name": _text(c, "name"), "title": _text(c, "label") or _text(c, "name")})
    for c in _iter(root, "CoverageSummary"):                           # WCS 1.1 / 2.0
        ident = _text(c, "Identifier") or _text(c, "CoverageId")
        if ident:
            layers.append({"name": ident, "title": _text(c, "Title") or ident})
    return {"version": root.get("version", ""), "layers": layers}


PARSERS = {"wms": parse_wms, "wmts": parse_wmts, "wfs": parse_wfs, "wcs": parse_wcs}


def parse_capabilities(kind, raw, url):
    """Odpowiedź GetCapabilities → {"type", "url", "title", "layers": [...], …}."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise ServiceError(tr("Odpowiedź nie jest poprawnym dokumentem XML – sprawdź adres i typ usługi.")) from None
    _exception(root)
    info = PARSERS[kind](root)
    info["layers"] = [ly for ly in info["layers"] if ly.get("name")]
    if not info["layers"]:
        raise ServiceError(tr("Nie znaleziono warstw – czy to na pewno usługa %s?") % kind.upper())
    svc = next((e for e in (_child(root, "Service"), _child(root, "ServiceIdentification")) if e is not None), root)
    info.update({"type": kind, "url": base_url(url), "title": _text(svc, "Title") or _text(svc, "label")})
    return info


# ------------------------------------------------------------------ dobór warstw

def norm(text):
    t = unicodedata.normalize("NFKC", str(text or "")).translate(_PL).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def match_layers(layers, wanted):
    """Warstwy usługi pasujące do nazw technicznych albo słów z tytułu (bez polskich znaków i wielkości liter)."""
    wanted = [w for w in (wanted if isinstance(wanted, list) else [wanted]) if str(w or "").strip()]
    if not wanted:
        return layers[:1] if len(layers) == 1 else []
    picked = []
    for w in wanted:
        wn = norm(w)
        tokens = [t for t in wn.split() if len(t) > 2 or t.isdigit()] or wn.split()
        best, best_score = None, 0
        for ly in layers:
            name, title = norm(ly.get("name")), norm(ly.get("title"))
            if str(ly.get("name", "")).strip().lower() == str(w).strip().lower():
                score = 1000                                            # dokładna nazwa techniczna
            elif wn and (wn == title or wn == name):
                score = 900
            else:
                hay = "%s %s" % (name, title)
                hits = sum(1 for t in tokens if t in hay)
                if not hits or hits < max(1, len(tokens) - 1):          # jedno słowo może nie pasować
                    continue
                score = 100 * hits / len(tokens) - len(title) / 100    # krótszy tytuł = trafniejszy
            if score > best_score:
                best, best_score = ly, score
        if best is not None and best not in picked:
            picked.append(best)
    return picked[:MAX_LAYERS_PER_STEP]


def pick_crs(available, preferred=()):
    """Układ dla zapytań: najpierw układ projektu, potem PUWG 1992, Web Mercator i WGS84."""
    known = [str(c).upper() for c in available or []]
    for c in list(preferred) + ["EPSG:2180", "EPSG:3857", "EPSG:4326"]:
        if c and c.upper() in known:
            return c.upper()
    return known[0] if known else None


def pick_matrix_set(sets, preferred=()):
    sets = sets or []
    for want in list(preferred) + ["EPSG:2180", "EPSG:3857"]:
        hit = next((m for m in sets if want and epsg(m.get("crs")).upper() == want.upper()), None)
        if hit:
            return hit
    return next((m for m in sets if re.search(r"3857|900913|google", "%s %s" % (m.get("crs"), m.get("id")), re.I)),
                sets[0] if sets else None)


def pick_format(formats):
    formats = formats or []
    return next((f for f in formats if f == "image/png"), next((f for f in formats if "png" in f),
                                                                 formats[0] if formats else "image/png"))


def layers_sample(layers, n=25):
    txt = ", ".join("„%s” (%s)" % (ly.get("title"), ly.get("name")) for ly in layers[:n])
    return txt + (" …" if len(layers) > n else "")


# ------------------------------------------------------------------ dane spod adresu

def remote_source(uri):
    """(adres, opcje) dla danych spod http(s) – także zapisanych jako /vsicurl/…|layername=…; inaczej None."""
    uri = str(uri or "").strip()
    # przedrostki wirtualnych systemów plików GDAL (/vsicurl/, /vsizip//vsicurl/ …) – dane pobiera wtyczka
    uri = re.sub(r"(?i)^/?(?:vsi[a-z0-9_]+/+)+", "", uri)
    base, _, rest = uri.partition("|")
    if not re.match(r"(?i)^https?://", base):
        return None
    opts = {}
    for part in filter(None, rest.split("|")):
        k, _, v = part.partition("=")
        opts[k.strip().lower()] = v.strip()
    return base, opts


# ------------------------------------------------------------------ BDOT10k (GUGiK, dane otwarte)
# Paczki powiatowe: https://opendata.geoportal.gov.pl/bdot10k/schemat2021/{GPKG|SHP}/<woj>/<powiat>_<FMT>.zip
# oraz (format pierwotny) …/schemat2021/<woj>/<powiat>_GML.zip. Pliki GML w paczce mają rozszerzenie .xml.
BDOT10K_BASE = "https://opendata.geoportal.gov.pl/bdot10k/schemat2021"
BDOT10K_FORMATS = ("GPKG", "SHP", "GML")      # kolejność prób: najmniejsze i najszybsze do odczytu najpierw
_BDOT_CLASS_RE = re.compile(r"(?i)\b(?:OT_)?([A-Z]{4})_([APL])\b")
_BDOT_POWIAT_RE = re.compile(r"\b(\d{4})(?:\d{2}(?:_\d)?)?\b")
BDOT10K_DATA_EXTS = (".gpkg", ".shp", ".gml", ".xml")


def bdot10k_powiat_code(value):
    """Czterocyfrowy TERYT powiatu z „1418”, „141805_2”, „141805_2.0001.12/3” albo „1418 (piaseczyński)”;
    None dla kodu województwa („14”) lub braku kodu."""
    m = _BDOT_POWIAT_RE.search(str(value or ""))
    return m.group(1) if m else None


def bdot10k_class(value):
    """Kod klasy BDOT10k w postaci kanonicznej, np. „OT_SKDR_L” (przyjmuje też „skdr_l”, „OT_SKDR_L – drogi”)."""
    m = _BDOT_CLASS_RE.search(str(value or ""))
    return "OT_%s_%s" % (m.group(1).upper(), m.group(2).upper()) if m else None


def bdot10k_package_urls(powiat):
    """Adresy paczki powiatowej w kolejności prób (GPKG, SHP, GML)."""
    woj = powiat[:2]
    return ["%s/GPKG/%s/%s_GPKG.zip" % (BDOT10K_BASE, woj, powiat),
            "%s/SHP/%s/%s_SHP.zip" % (BDOT10K_BASE, woj, powiat),
            "%s/%s/%s_GML.zip" % (BDOT10K_BASE, woj, powiat)]


def bdot10k_members(names, cls):
    """(pliki nazwane kodem klasy w kolejności preferencji formatu, pozostałe GeoPackage – klasa może być w nich
    tabelą). Pomija pliki pomocnicze i katalog __MACOSX."""
    cls_l = cls.lower()
    data = [n for n in names if n.lower().endswith(BDOT10K_DATA_EXTS) and not n.startswith("__MACOSX")]
    named = sorted((n for n in data if cls_l in os.path.basename(n).lower()),
                   key=lambda n: BDOT10K_DATA_EXTS.index(os.path.splitext(n.lower())[1]))
    gpkgs = [n for n in data if n.lower().endswith(".gpkg") and n not in named]
    return named, gpkgs


def is_overpass(url):
    parts = urlsplit(url)
    return "overpass" in parts.netloc.lower() or parts.path.rstrip("/").endswith("/interpreter")


def overpass_readable(url):
    """Zapytanie Overpass w postaci, którą odczyta GDAL: format XML i geometria jako osobne punkty.

    „out geom;” zapisuje współrzędne wewnątrz linii (bez elementów <node>) – sterownik OSM GDAL-a nie odbuduje
    z tego obiektów. Zamieniamy na „out body; >; out skel qt;”, a „[out:json]” na „[out:xml]”.
    """
    if not is_overpass(url):
        return url
    parts = urlsplit(url)
    changed, out = False, []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k == "data":
            nv = re.sub(r"\[out:json\]", "[out:xml]", v, flags=re.I)
            nv = re.sub(r"\bout\s+geom(?:\s+qt)?\s*;", "out body;>;out skel qt;", nv, flags=re.I)
            changed = changed or nv != v
            v = nv
        out.append((k, v))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(out), parts.fragment)) if changed else url


# Publiczne instancje Overpass z danymi dla całego świata (wiki.openstreetmap.org/wiki/Overpass_API).
# Kolejność ma znaczenie: pierwszy jest serwer główny. Instancje regionalne (np. osm.ch) i wyłączone
# (np. openstreetmap.fr – zakomentowana także w QuickOSM) nie nadają się – zwracają puste wyniki albo błędy.
OVERPASS_SERVERS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",   # dawniej overpass.kumi.systems
    "https://z.overpass-api.de/api/interpreter",          # drugi węzeł serwera głównego
)
OVERPASS_HOSTS = ("overpass-api.de", "www.overpass-api.de", "lz4.overpass-api.de", "z.overpass-api.de")
OVERPASS_MIRRORS = OVERPASS_SERVERS[1:]


def overpass_mirror_urls(url):
    """Ten sam zapytanie na serwerach zapasowych (gdy główny serwer Overpass jest przeciążony)."""
    parts = urlsplit(url)
    if parts.netloc.lower() not in OVERPASS_HOSTS:
        return []
    out = []
    for mirror in OVERPASS_MIRRORS:
        m = urlsplit(mirror)
        out.append(urlunsplit((m.scheme, m.netloc, m.path, parts.query, "")))
    return out


# Błędy QuickOSM / Overpass, które wynikają z przeciążenia serwera, a nie z zapytania
_OVERPASS_TRANSIENT = re.compile(
    r"NetWorkErrorException|OverpassTimeoutException|OverpassManyRequestException|Gateway Timeout|Bad Gateway|"
    r"Service Unavailable|Too Many Requests|Internal Server Error|timed out|Connection refused|"
    r"Connection closed|Host .* not found|\b(?:429|500|502|503|504)\b", re.I)
_OVERPASS_SERVER_IN_ERROR = re.compile(r"(https?://[^\s?'\"]+?/interpreter)")


def overpass_transient(text):
    """Czy błąd QuickOSM/Overpass to chwilowe przeciążenie serwera (warto ponowić na innym serwerze)."""
    return bool(_OVERPASS_TRANSIENT.search(str(text or "")))


def overpass_server_in_error(text):
    m = _OVERPASS_SERVER_IN_ERROR.search(str(text or ""))
    return m.group(1) if m else None


def known_overpass_server(url):
    host = (urlsplit(str(url or "")).hostname or "").lower()
    return any(host == (urlsplit(s).hostname or "") for s in OVERPASS_SERVERS)


def next_overpass_server(tried):
    """Pierwszy serwer z listy, którego jeszcze nie próbowano (porównanie po nazwie hosta)."""
    hosts = {(urlsplit(str(t or "")).hostname or "").lower() for t in tried}
    if "overpass-api.de" in hosts or "lz4.overpass-api.de" in hosts:
        hosts.add("overpass-api.de")
    return next((s for s in OVERPASS_SERVERS if (urlsplit(s).hostname or "") not in hosts), None)


def overpass_error(head):
    low = (head or b"").lower()
    return b"runtime error" in low or (b"<remark>" in low and b"error" in low)


def sniff_ext(head, ctype, url):
    """Rozszerzenie pliku na podstawie początku danych, typu MIME i adresu."""
    h = (head or b"").lstrip()[:600].lower()
    ctype = (ctype or "").lower()
    if (head or b"")[:2] == b"PK":
        return ".zip"
    if (head or b"")[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif"
    if (head or b"")[:16].startswith(b"SQLite format 3"):
        return ".gpkg"
    if "json" in ctype or h[:1] in (b"{", b"["):
        return ".geojson"
    if h.startswith((b"<!doctype html", b"<html")) or "text/html" in ctype:
        return None                                     # strona WWW (np. komunikat błędu), a nie dane
    if b"<osm" in h:
        return ".osm"
    if b"<kml" in h:
        return ".kml"
    path = str(url or "").split("?")[0].lower()
    for ext in (".gpkg", ".geojson", ".json", ".kml", ".gml", ".zip", ".csv", ".tif", ".tiff", ".osm", ".pbf"):
        if path.endswith(ext):
            return ext
    if h.startswith(b"<?xml") or h.startswith(b"<"):
        return ".gml"
    return None


def busy_status(status):
    return status in (429, 502, 503, 504)
