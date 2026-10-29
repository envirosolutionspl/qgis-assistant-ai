# -*- coding: utf-8 -*-
"""Warstwa protokołu serwera MCP (Model Context Protocol).

Moduł nie zależy od Qt ani QGIS, więc jest testowalny. Serwer w QGIS przyjmuje
JSON-RPC 2.0 metodą POST na /mcp (zgodnie z transportem „Streamable HTTP” MCP
w wersji bez strumienia zdarzeń), a Claude Desktop rozmawia z nim przez most
stdio (mcp_bridge.py). Ten moduł zawiera: parser żądań HTTP, budowanie
odpowiedzi, katalog narzędzi (nazwa + schemat JSON + mapowanie na krok planu)
i dyspozytor JSON-RPC, któremu wykonanie narzędzia dostarcza się z zewnątrz
(wywołanie zwrotne, bo kroki w QGIS są asynchroniczne).
"""
import hashlib
import hmac
import json
from urllib.parse import urlsplit

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "gis-assistant-ai-qgis"
# 4 MB – plan z wieloma krokami to kilka kB; większe żądania odrzucamy
MAX_BODY = 4 * 1048576

# Błędy JSON-RPC (standard)
(PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS,
 INTERNAL_ERROR) = -32700, -32600, -32601, -32602, -32603
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


# ------------------------------------------------------------------ narzędzia
def _schema(props, required=()):
    return {"type": "object", "properties": props,
            "required": list(required), "additionalProperties": False}


_LAYER_REF = {"type": "string",
              "description": "Identyfikator warstwy (pole „id” "
                             "z qgis_context) albo jej nazwa."}
_ALLOW_INTERNAL = {"type": "boolean", "default": False,
                   "description": "Zgoda na adres w sieci "
                                  "wewnętrznej/localhost (domyślnie takie "
                                  "adresy są odrzucane ze względów "
                                  "bezpieczeństwa)."}

TOOLS = [
    {
        "name": "qgis_context",
        "description": "Opis bieżącego projektu QGIS: wersja, układ "
                       "współrzędnych, zasięg mapy, warstwy (id, nazwa, "
                       "typ geometrii, układ, liczba obiektów, pola), aktywna "
                       "warstwa, dostawcy Processing i algorytmy wtyczek. "
                       "Wywołuj na początku pracy i po zmianach w projekcie.",
        "inputSchema": _schema({
            "samples": {"type": "boolean", "default": False,
                        "description": "Dołącz przykładowe wartości pól "
                                       "tekstowych (maks. 5 na pole)."}}),
    },
    {
        "name": "layer_info",
        "description": "Szczegóły jednej warstwy: pola z typami, układ, "
                       "zasięg, liczba obiektów; opcjonalnie przykładowe "
                       "wartości atrybutów.",
        "inputSchema": _schema(
            {"layer": _LAYER_REF,
             "samples": {"type": "boolean", "default": True}}, ["layer"]),
    },
    {
        "name": "list_algorithms",
        "description": "Wyszukuje algorytmy Processing po fragmencie "
                       "identyfikatora lub nazwy (np. „buffer”, „clip”, "
                       "„quickosm”). Zwraca id, nazwę i dostawcę (maks. 50).",
        "inputSchema": _schema(
            {"query": {"type": "string",
                       "description": "Fragment nazwy lub identyfikatora."}},
            ["query"]),
    },
    {
        "name": "algorithm_help",
        "description": "Parametry algorytmu Processing: nazwa, typ, opis, "
                       "wartość domyślna, opcje (dla list wyboru – "
                       "z numerami), czy wymagany. Użyj przed "
                       "run_processing, gdy nie znasz parametrów.",
        "inputSchema": _schema(
            {"algorithm": {"type": "string",
                           "description": "Identyfikator, np. "
                                          "native:buffer."}},
            ["algorithm"]),
    },
    {
        "name": "run_processing",
        "description": "Uruchamia algorytm Processing i dodaje wynik do "
                       "projektu. Warstwy wejściowe podaj jako id lub nazwę "
                       "warstwy projektu (pliki z dysku nie są dozwolone). "
                       "Wyjścia pomiń albo podaj „TEMPORARY_OUTPUT” – wyniki "
                       "są zawsze warstwami tymczasowymi, zapis do pliku "
                       "wykonuje użytkownik. Odległości są w jednostkach "
                       "układu warstwy (warstwy w stopniach najpierw przelicz "
                       "native:reprojectlayer do EPSG:2180).",
        "inputSchema": _schema({
            "algorithm": {"type": "string",
                          "description": "Identyfikator, np. native:buffer."},
            "params": {"type": "object",
                       "description": "Parametry algorytmu (dokładne nazwy "
                                      "QGIS).",
                       "additionalProperties": True},
            "output_name": {"type": "string",
                            "description": "Nazwa warstwy wynikowej "
                                           "w projekcie."},
            "selected_only": {"type": "boolean", "default": False,
                              "description": "Tylko zaznaczone obiekty "
                                             "warstwy INPUT."}},
            ["algorithm", "params"]),
        "step": "processing",
    },
    {
        "name": "load_layer",
        "description": "Wczytuje warstwę: usługa WMS/WFS/XYZ (uri w składni "
                       "QGIS) albo dane spod adresu http(s) (GeoJSON, GPKG, "
                       "ZIP, KML, GML, zapytanie Overpass API – provider "
                       "„ogr”; wtyczka sama pobierze plik). Nie zgaduj "
                       "adresów usług – do nieznanych usług użyj "
                       "add_service.",
        "inputSchema": _schema({
            "provider": {"type": "string",
                         "enum": ["wms", "wfs", "xyz", "ogr", "gdal", "oapif",
                                  "arcgisfeatureserver"]},
            "uri": {"type": "string"},
            "name": {"type": "string",
                     "description": "Nazwa warstwy w projekcie."},
            "allow_internal_network": _ALLOW_INTERNAL},
            ["provider", "uri", "name"]),
        "step": "load_layer",
    },
    {
        "name": "add_service",
        "description": "Dodaje warstwy z usługi WMS/WMTS/WFS/WCS: wtyczka "
                       "pobiera GetCapabilities, dopasowuje warstwy po "
                       "nazwach/tytułach (dopasowanie luźne, po słowach "
                       "kluczowych) i przybliża mapę do zasięgu usługi. "
                       "Podaj adres bazowy usługi.",
        "inputSchema": _schema({
            "service_type": {"type": "string",
                             "enum": ["wms", "wmts", "wfs", "wcs"]},
            "url": {"type": "string"},
            "layers": {"type": "array", "items": {"type": "string"},
                       "description": "Nazwy lub słowa kluczowe szukanych "
                                      "warstw (puste = pierwsza)."},
            "allow_internal_network": _ALLOW_INTERNAL},
            ["service_type", "url"]),
        "step": "add_service",
    },
    {
        "name": "uldk_boundary",
        "description": "Granica jednostki administracyjnej lub działki "
                       "z usługi ULDK GUGiK (Polska), EPSG:2180. TERYT: "
                       "województwo „14”, powiat „1418”, gmina „141805_2”, "
                       "obręb „141805_2.0001”, działka "
                       "„141805_2.0001.123/4”. Można podać listę kodów.",
        "inputSchema": _schema({
            "level": {"type": "string",
                      "enum": ["wojewodztwo", "powiat", "gmina", "obreb",
                               "dzialka"]},
            "teryt": {"oneOf": [{"type": "string"},
                                {"type": "array",
                                 "items": {"type": "string"}}]},
            "name": {"type": "string",
                     "description": "Nazwa warstwy w projekcie."}},
            ["level", "teryt"]),
        "step": "uldk_boundary",
    },
    {
        "name": "bdot10k_layer",
        "description": "Pobiera paczkę powiatową BDOT10k z danych otwartych "
                       "GUGiK (GPKG, awaryjnie SHP/GML) i wczytuje jedną "
                       "klasę obiektów, np. budynki OT_BUBD_A, drogi "
                       "OT_SKDR_L, jezdnie OT_SKJZ_L, kompleksy oświatowe "
                       "OT_KUOS_A, wody OT_PTWP_A, lasy OT_PTLZ_A, "
                       "miejscowości OT_ADMS_P. Paczka obejmuje cały powiat "
                       "(dziesiątki–setki MB, pamiętana na czas sesji). "
                       "Nazwy pól zależą od formatu – po wczytaniu sprawdź je "
                       "przez layer_info.",
        "inputSchema": _schema({
            "teryt": {"type": "string",
                      "description": "TERYT powiatu (4 cyfry); kod gminy też "
                                     "zadziała."},
            "class": {"type": "string",
                      "description": "Kod klasy, np. OT_BUBD_A."},
            "name": {"type": "string",
                     "description": "Nazwa warstwy w projekcie."}},
            ["teryt", "class"]),
        "step": "bdot10k_layer",
    },
    {
        "name": "zoom_to_layer",
        "description": "Przybliża mapę do zasięgu warstwy.",
        "inputSchema": _schema({"layer": _LAYER_REF}, ["layer"]),
        "step": "zoom",
    },
    {
        "name": "set_layer_style",
        "description": "Zmienia wygląd warstwy w projekcie: krycie (albo "
                       "przezroczystość), kolor wypełnienia i obrysu, "
                       "szerokość linii/obrysu, rozmiar punktów, widoczność "
                       "oraz pozycję w drzewie warstw (np. podkład na spód). "
                       "Kolory stosują się do symbolu pojedynczego; dla "
                       "symbolizacji kategoryzowanej zmienia się tylko "
                       "krycie, widoczność i pozycja.",
        "inputSchema": _schema({
            "layer": _LAYER_REF,
            "opacity": {"type": "number", "minimum": 0, "maximum": 100,
                        "description": "Krycie warstwy w procentach (100 = "
                                       "nieprzezroczysta)."},
            "transparency": {"type": "number", "minimum": 0, "maximum": 100,
                             "description": "Przezroczystość w procentach "
                                            "(odwrotność krycia; podaj jedno "
                                            "z dwóch)."},
            "fill_color": {"type": "string",
                           "description": "Kolor wypełnienia/punktów, np. "
                                          "#ff8800 lub nazwa CSS."},
            "stroke_color": {"type": "string",
                             "description": "Kolor obrysu (poligony, punkty) "
                                            "lub linii."},
            "stroke_width": {"type": "number", "minimum": 0,
                             "description": "Szerokość obrysu lub linii "
                                            "w mm."},
            "size": {"type": "number", "minimum": 0,
                     "description": "Rozmiar symbolu punktowego w mm."},
            "visible": {"type": "boolean",
                        "description": "Włącz/wyłącz widoczność warstwy."},
            "position": {"type": "string", "enum": ["top", "bottom"],
                         "description": "Przenieś warstwę na wierzch lub na "
                                        "spód drzewa warstw."}},
            ["layer"]),
    },
    {
        "name": "run_plan",
        "description": "Wykonuje kilka kroków po kolei w jednym wywołaniu "
                       "(format kroków jak w pojedynczych narzędziach: pole "
                       "„action” = processing | load_layer | add_service | "
                       "uldk_boundary | bdot10k_layer | zoom, plus pola danej "
                       "akcji). Wynik kroku wskazuj w kolejnych krokach "
                       "referencją \"{{s1}}\" (identyfikator warstwy) albo "
                       "\"{{s1.NAZWA_WYJŚCIA}}\". Kroki user_action i python "
                       "nie są dostępne przez MCP.",
        "inputSchema": _schema({
            "title": {"type": "string"},
            "steps": {"type": "array", "minItems": 1, "items": {
                "type": "object",
                "properties": {"id": {"type": "string"},
                               "action": {"type": "string"},
                               "title": {"type": "string"}},
                "required": ["action"], "additionalProperties": True}},
            "allow_internal_network": _ALLOW_INTERNAL},
            ["steps"]),
    },
]

TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}
MCP_FORBIDDEN_ACTIONS = ("user_action", "python", "processing_dialog", "note")


# --------------------------------------------------- język opisów (dla modelu)
# Opisy narzędzi są tekstem dla modelu, nie interfejsem QGIS, więc nie
# przechodzą przez tr(); wersja angielska jest wybierana, gdy język interfejsu
# QGIS jest inny niż polski (tak jak tłumaczenie wtyczki).
_EN = {
    'Identyfikator warstwy (pole „id” z qgis_context) albo jej nazwa.':
        'Layer id (the “id” field from qgis_context) or its name.',
    'Zgoda na adres w sieci wewnętrznej/localhost (domyślnie takie adresy są '
    'odrzucane ze względów bezpieczeństwa).':
        'Consent for an internal-network/localhost address (such addresses '
        'are rejected by default for security).',
    'Opis bieżącego projektu QGIS: wersja, układ współrzędnych, zasięg mapy, '
    'warstwy (id, nazwa, typ geometrii, układ, liczba obiektów, pola), '
    'aktywna warstwa, dostawcy Processing i algorytmy wtyczek. Wywołuj na '
    'początku pracy i po zmianach w projekcie.':
        'Description of the current QGIS project: version, CRS, map extent, '
        'layers (id, name, geometry type, CRS, feature count, fields), active '
        'layer, Processing providers and plugin algorithms. Call it at the '
        'start and after the project changes.',
    'Dołącz przykładowe wartości pól tekstowych (maks. 5 na pole).':
        'Include sample values of text fields (max. 5 per field).',
    'Szczegóły jednej warstwy: pola z typami, układ, zasięg, liczba obiektów; '
    'opcjonalnie przykładowe wartości atrybutów.':
        'Details of one layer: fields with types, CRS, extent, feature count; '
        'optionally sample attribute values.',
    'Wyszukuje algorytmy Processing po fragmencie identyfikatora lub nazwy '
    '(np. „buffer”, „clip”, „quickosm”). Zwraca id, nazwę i dostawcę (maks. '
    '50).':
        'Searches Processing algorithms by a fragment of the id or name (e.g. '
        '“buffer”, “clip”, “quickosm”). Returns id, name and provider (max. '
        '50).',
    'Fragment nazwy lub identyfikatora.':
        'Fragment of the name or id.',
    'Parametry algorytmu Processing: nazwa, typ, opis, wartość domyślna, '
    'opcje (dla list wyboru – z numerami), czy wymagany. Użyj przed '
    'run_processing, gdy nie znasz parametrów.':
        'Parameters of a Processing algorithm: name, type, description, '
        'default, options (for enums – numbered), whether required. Use '
        'before run_processing when you do not know the parameters.',
    'Identyfikator, np. native:buffer.':
        'Identifier, e.g. native:buffer.',
    'Uruchamia algorytm Processing i dodaje wynik do projektu. Warstwy '
    'wejściowe podaj jako id lub nazwę warstwy projektu (pliki z dysku nie są '
    'dozwolone). Wyjścia pomiń albo podaj „TEMPORARY_OUTPUT” – wyniki są '
    'zawsze warstwami tymczasowymi, zapis do pliku wykonuje użytkownik. '
    'Odległości są w jednostkach układu warstwy (warstwy w stopniach najpierw '
    'przelicz native:reprojectlayer do EPSG:2180).':
        'Runs a Processing algorithm and adds the result to the project. Give '
        'input layers as the id or name of a project layer (files on disk are '
        'not allowed). Omit outputs or pass “TEMPORARY_OUTPUT” – results are '
        'always temporary layers; saving to a file is up to the user. '
        'Distances are in the layer CRS units (reproject layers in degrees '
        'first with native:reprojectlayer, e.g. to EPSG:2180 for Poland).',
    'Parametry algorytmu (dokładne nazwy QGIS).':
        'Algorithm parameters (exact QGIS names).',
    'Nazwa warstwy wynikowej w projekcie.':
        'Name of the output layer in the project.',
    'Tylko zaznaczone obiekty warstwy INPUT.':
        'Only selected features of the INPUT layer.',
    'Wczytuje warstwę: usługa WMS/WFS/XYZ (uri w składni QGIS) albo dane spod '
    'adresu http(s) (GeoJSON, GPKG, ZIP, KML, GML, zapytanie Overpass API – '
    'provider „ogr”; wtyczka sama pobierze plik). Nie zgaduj adresów usług – '
    'do nieznanych usług użyj add_service.':
        'Loads a layer: a WMS/WFS/XYZ service (uri in QGIS syntax) or data '
        'from an http(s) address (GeoJSON, GPKG, ZIP, KML, GML, Overpass API '
        'query – provider “ogr”; the plugin downloads the file). Do not guess '
        'service addresses – use add_service for unknown services.',
    'Nazwa warstwy w projekcie.':
        'Layer name in the project.',
    'Dodaje warstwy z usługi WMS/WMTS/WFS/WCS: wtyczka pobiera '
    'GetCapabilities, dopasowuje warstwy po nazwach/tytułach (dopasowanie '
    'luźne, po słowach kluczowych) i przybliża mapę do zasięgu usługi. Podaj '
    'adres bazowy usługi.':
        'Adds layers from a WMS/WMTS/WFS/WCS service: the plugin fetches '
        'GetCapabilities, matches layers by names/titles (loose, '
        'keyword-based matching) and zooms the map to the service extent. '
        'Pass the service base URL.',
    'Nazwy lub słowa kluczowe szukanych warstw (puste = pierwsza).':
        'Names or keywords of the wanted layers (empty = first layer).',
    'Granica jednostki administracyjnej lub działki z usługi ULDK GUGiK '
    '(Polska), EPSG:2180. TERYT: województwo „14”, powiat „1418”, gmina '
    '„141805_2”, obręb „141805_2.0001”, działka „141805_2.0001.123/4”. Można '
    'podać listę kodów.':
        'Boundary of an administrative unit or cadastral parcel from the '
        'Polish ULDK (GUGiK) service, EPSG:2180. TERYT: voivodeship “14”, '
        'county “1418”, commune “141805_2”, cadastral district '
        '“141805_2.0001”, parcel “141805_2.0001.123/4”. A list of codes is '
        'accepted.',
    'Pobiera paczkę powiatową BDOT10k z danych otwartych GUGiK (GPKG, '
    'awaryjnie SHP/GML) i wczytuje jedną klasę obiektów, np. budynki '
    'OT_BUBD_A, drogi OT_SKDR_L, jezdnie OT_SKJZ_L, kompleksy oświatowe '
    'OT_KUOS_A, wody OT_PTWP_A, lasy OT_PTLZ_A, miejscowości OT_ADMS_P. '
    'Paczka obejmuje cały powiat (dziesiątki–setki MB, pamiętana na czas '
    'sesji). Nazwy pól zależą od formatu – po wczytaniu sprawdź je przez '
    'layer_info.':
        'Downloads a county BDOT10k package from GUGiK open data (GPKG, '
        'falling back to SHP/GML) and loads one feature class, e.g. buildings '
        'OT_BUBD_A, roads OT_SKDR_L, carriageways OT_SKJZ_L, education '
        'complexes OT_KUOS_A, surface water OT_PTWP_A, forests OT_PTLZ_A, '
        'localities OT_ADMS_P. The package covers the whole county '
        '(tens–hundreds of MB, cached for the session). Field names depend on '
        'the format – check them with layer_info after loading.',
    'TERYT powiatu (4 cyfry); kod gminy też zadziała.':
        'County TERYT code (4 digits); a commune code also works.',
    'Kod klasy, np. OT_BUBD_A.':
        'Class code, e.g. OT_BUBD_A.',
    'Zmienia wygląd warstwy w projekcie: krycie (albo przezroczystość), kolor '
    'wypełnienia i obrysu, szerokość linii/obrysu, rozmiar punktów, '
    'widoczność oraz pozycję w drzewie warstw (np. podkład na spód). Kolory '
    'stosują się do symbolu pojedynczego; dla symbolizacji kategoryzowanej '
    'zmienia się tylko krycie, widoczność i pozycja.':
        'Changes a layer’s appearance in the project: opacity (or '
        'transparency), fill and stroke colour, line/stroke width, point '
        'size, visibility and position in the layer tree (e.g. basemap to the '
        'bottom). Colours apply to single-symbol renderers; for categorized '
        'symbology only opacity, visibility and position change.',
    'Krycie warstwy w procentach (100 = nieprzezroczysta).':
        'Layer opacity in percent (100 = opaque).',
    'Przezroczystość w procentach (odwrotność krycia; podaj jedno z dwóch).':
        'Transparency in percent (inverse of opacity; pass one of the two).',
    'Kolor wypełnienia/punktów, np. #ff8800 lub nazwa CSS.':
        'Fill/point colour, e.g. #ff8800 or a CSS name.',
    'Kolor obrysu (poligony, punkty) lub linii.':
        'Stroke colour (polygons, points) or line colour.',
    'Szerokość obrysu lub linii w mm.': 'Stroke or line width in mm.',
    'Rozmiar symbolu punktowego w mm.': 'Point symbol size in mm.',
    'Włącz/wyłącz widoczność warstwy.': 'Turn layer visibility on/off.',
    'Przenieś warstwę na wierzch lub na spód drzewa warstw.':
        'Move the layer to the top or bottom of the layer tree.',
    'Przybliża mapę do zasięgu warstwy.':
        'Zooms the map to the layer extent.',
    'Wykonuje kilka kroków po kolei w jednym wywołaniu (format kroków jak w '
    'pojedynczych narzędziach: pole „action” = processing | load_layer | '
    'add_service | uldk_boundary | bdot10k_layer | zoom, plus pola danej '
    'akcji). Wynik kroku wskazuj w kolejnych krokach referencją "{{s1}}" '
    '(identyfikator warstwy) albo "{{s1.NAZWA_WYJŚCIA}}". Kroki user_action i '
    'python nie są dostępne przez MCP.':
        'Runs several steps in sequence in one call (step format as in the '
        'single tools: field “action” = processing | load_layer | add_service '
        '| uldk_boundary | bdot10k_layer | zoom, plus that action’s fields). '
        'Reference a step result in later steps with "{{s1}}" (layer id) or '
        '"{{s1.OUTPUT_NAME}}". user_action and python steps are not available '
        'via MCP.',
}


def normalize_lang(lang):
    """Kod języka opisów: „pl” dla polskiego, „en” dla każdego innego."""
    return "pl" if str(lang or "pl").lower().startswith("pl") else "en"


def _localize(obj, lang):
    if lang == "pl":
        return obj
    if isinstance(obj, dict):
        return {k: (_EN.get(v, v)
                    if k == "description" and isinstance(v, str)
                    else _localize(v, lang))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_localize(v, lang) for v in obj]
    return obj


def public_tools(lang="pl"):
    """Lista narzędzi dla tools/list w języku interfejsu QGIS.

    Bez wewnętrznego pola „step”.
    """
    return _localize([{k: v for k, v in t.items() if k != "step"}
                      for t in TOOLS], normalize_lang(lang))


def tool_to_step(name, args):
    """Krok planu (format executora) z wywołania narzędzia.

    Zwraca None dla narzędzi obsługiwanych inaczej niż przez plan.
    """
    tool = TOOLS_BY_NAME.get(name)
    if not tool or "step" not in tool:
        return None
    args = dict(args or {})
    args.pop("allow_internal_network", None)
    step = {"id": "s1", "action": tool["step"], "title": name}
    if name == "run_processing":
        step["algorithm"] = args.get("algorithm", "")
        params = dict(args.get("params") or {})
        if (args.get("selected_only") and "INPUT" in params
                and not isinstance(params["INPUT"], dict)):
            params["INPUT"] = {"source": params["INPUT"],
                               "selected_only": True}
        step["params"] = params
        if args.get("output_name"):
            step["output_name"] = args["output_name"]
        step["title"] = (args.get("output_name") or args.get("algorithm")
                         or name)
        return step
    step.update(args)
    for key in ("name", "output_name", "class", "algorithm"):
        if args.get(key):
            step["title"] = str(args[key])
            break
    return step


def plan_from_args(args):
    """Plan dla run_plan: kroki z numeracją id s1… (gdy brak).

    Akcje zabronione przez MCP odrzuca dopiero serwer.
    """
    steps = []
    for i, s in enumerate(args.get("steps") or [], 1):
        s = dict(s)
        s.setdefault("id", "s%d" % i)
        s.setdefault("title", s.get("name") or s.get("output_name")
                     or s.get("algorithm") or s["action"])
        steps.append(s)
    return {"type": "plan", "title": args.get("title") or "MCP",
            "steps": steps}


# ----------------------------------------------------------------------- HTTP
def parse_http_request(buf):
    """Rozbierz żądanie HTTP z bufora.

    Zwraca (metoda, ścieżka, nagłówki{małe litery}, treść, liczba zużytych
    bajtów) albo None, gdy żądanie jest niepełne. Zgłasza ValueError dla
    żądań zniekształconych lub zbyt dużych.
    """
    end = buf.find(b"\r\n\r\n")
    if end < 0:
        if len(buf) > 64 * 1024:
            raise ValueError("headers too large")
        return None
    head = buf[:end].decode("iso-8859-1")
    lines = head.split("\r\n")
    try:
        method, path, _version = lines[0].split(" ", 2)
    except ValueError:
        raise ValueError("bad request line") from None
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    try:
        length = int(headers.get("content-length", "0"))
    except ValueError:
        raise ValueError("bad content-length") from None
    if length > MAX_BODY:
        raise ValueError("body too large")
    body_start = end + 4
    if len(buf) < body_start + length:
        return None
    return (method.upper(), path, headers,
            bytes(buf[body_start:body_start + length]), body_start + length)


_STATUS = {200: "OK", 202: "Accepted", 400: "Bad Request",
           401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
           405: "Method Not Allowed"}


def http_response(status, body=b""):
    """Pełna odpowiedź HTTP/1.1 (JSON, Connection: close) jako bajty."""
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    elif isinstance(body, str):
        body = body.encode("utf-8")
    head = ("HTTP/1.1 %d %s\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\nCache-Control: no-store\r\n\r\n"
            % (status, _STATUS.get(status, "OK"), len(body)))
    return head.encode("iso-8859-1") + body


def origin_allowed(headers):
    """Czy nagłówek Origin (jeśli jest) wskazuje localhost.

    Ochrona przed DNS rebinding (wymóg specyfikacji MCP). Klienci spoza
    przeglądarki (most stdio) nie wysyłają Origin – takie żądania przechodzą
    dalej do sprawdzenia tokenu.
    """
    origin = headers.get("origin")
    if origin is None:
        return True
    try:
        parts = urlsplit(origin.strip())
        # .port zgłasza ValueError dla nieprawidłowego portu
        host, _ = parts.hostname, parts.port
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and host in LOCAL_HOSTS


def token_digest(token):
    """Skrót SHA-256 tokenu (szesnastkowo) – tylko on trafia do ustawień."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authorized(headers, digest):
    """Czy żądanie ma token serwera.

    Skrót tokenu z nagłówka Authorization: Bearer <token> (albo X-Token)
    musi zgadzać się ze skrótem zapisanym przez serwer (``token_digest``).
    """
    if not digest:
        return False
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        sent = auth[7:].strip()
    else:
        sent = headers.get("x-token", "")
    if not sent:
        return False
    # porównanie w stałym czasie
    return hmac.compare_digest(token_digest(sent), digest)


# ------------------------------------------------------------------- JSON-RPC
def rpc_result(msg_id, result):
    """Odpowiedź JSON-RPC z wynikiem."""
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def rpc_error(msg_id, code, message, data=None):
    """Odpowiedź JSON-RPC z błędem (data – opcjonalne szczegóły)."""
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def tool_text(text, is_error=False, structured=None):
    """Wynik narzędzia w formacie MCP.

    content: text; opcjonalnie structuredContent.
    """
    out = {"content": [{"type": "text", "text": text}],
           "isError": bool(is_error)}
    if structured is not None:
        out["structuredContent"] = structured
    return out


class Dispatcher:
    """Obsługa metod MCP.

    Narzędzia wykonuje `call_tool(name, args, respond)` – respond(result_dict)
    może zostać wywołane później (asynchronicznie). `respond` dla handle()
    dostaje gotową odpowiedź JSON-RPC albo None (powiadomienie – bez
    odpowiedzi).
    """

    def __init__(self, call_tool, version="", instructions="", lang="pl"):
        """Utwórz dyspozytor z funkcją wykonującą narzędzia."""
        self._call_tool = call_tool
        self._version = version
        self._instructions = instructions
        self.lang = normalize_lang(lang)

    def handle(self, msg, respond):
        """Obsłuż komunikat JSON-RPC; odpowiedź trafia do respond()."""
        if (not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0"
                or not isinstance(msg.get("method"), str)):
            respond(rpc_error(msg.get("id") if isinstance(msg, dict) else None,
                              INVALID_REQUEST, "Invalid Request"))
            return
        method, msg_id, params = (msg["method"], msg.get("id"),
                                  msg.get("params"))
        # powiadomienie – bez odpowiedzi
        if msg_id is None:
            respond(None)
            return
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            respond(rpc_error(msg_id, INVALID_PARAMS,
                              "params must be an object"))
            return
        if method == "initialize":
            respond(rpc_result(msg_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME,
                               "version": self._version},
                "instructions": self._instructions}))
        elif method == "ping":
            respond(rpc_result(msg_id, {}))
        elif method == "tools/list":
            respond(rpc_result(msg_id, {"tools": public_tools(self.lang)}))
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name not in TOOLS_BY_NAME:
                respond(rpc_error(msg_id, INVALID_PARAMS,
                                  "Unknown tool: %s" % name))
                return
            if not isinstance(args, dict):
                respond(rpc_error(msg_id, INVALID_PARAMS,
                                  "arguments must be an object"))
                return
            self._call_tool(name, args, lambda result, i=msg_id: respond(
                rpc_result(i, result)))
        elif method in ("resources/list", "prompts/list"):
            respond(rpc_result(msg_id, {"resources": [], "prompts": []}))
        else:
            respond(rpc_error(msg_id, METHOD_NOT_FOUND,
                              "Method not found: %s" % method))


def claude_desktop_config(python_exe, bridge_path, url, token,
                          server_key="qgis-gis-assistant", lang="pl"):
    """Fragment claude_desktop_config.json uruchamiający most stdio."""
    return {"mcpServers": {server_key: {
        "command": python_exe,
        "args": [bridge_path, "--url", url, "--lang", normalize_lang(lang)],
        "env": {"GIS_ASSISTANT_MCP_TOKEN": token}}}}
