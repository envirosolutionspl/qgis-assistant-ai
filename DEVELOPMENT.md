# GIS Assistant AI – dokumentacja techniczna

Panel z linią poleceń, w której opisujesz językiem naturalnym, co chcesz zrobić w QGIS.
Wtyczka odpowiada na dwa sposoby:

* **Narzędzie** – przy prostych pytaniach („jak połączyć obiekty w jeden?”) wskazuje algorytm
  lub narzędzie wraz ze ścieżką w menu (np. *Wektor › Narzędzia geoprocesingu › Agreguj*),
  przyciskiem „Otwórz narzędzie” albo linkiem do wtyczki w repozytorium
  (np. <https://plugins.qgis.org/plugins/pobieracz_danych_gugik/>).
* **Plan działań** – przy zadaniach („Stwórz bufor 100 m od szkół w powiecie piaseczyńskim”)
  przygotowuje ponumerowany plan krok po kroku. Po jego wyświetleniu odblokowuje się przycisk
  **WYKONAJ**, który realizuje plan automatycznie.

Jeżeli krok wymaga Twojej akcji (podłączenie usługi WMS, pobranie paczki BDOT10k, wybór pliku),
plan zatrzymuje się i wyświetla komunikat. Po kliknięciu **„Wykonałem – kontynuuj”** (i ewentualnym
wskazaniu wczytanej warstwy) AI dopasowuje dalsze kroki do rzeczywistej struktury danych
i wykonanie jest kontynuowane. Gdy krok się nie powiedzie, możesz poprosić AI o naprawę,
ponowić, pominąć krok lub przerwać plan.

## Instalacja

1. QGIS: *Wtyczki › Zarządzaj wtyczkami › Zainstaluj z pliku ZIP* → wskaż `gis_assistant_ai-<wersja>.zip`
   z [wydań na GitHubie](https://github.com/envirosolutionspl/qgis-assistant-ai/releases).
   Jeśli masz starszą wersję (katalog `asystent_ai` lub `gis_assistant`), najpierw ją odinstaluj – ustawienia i klucz API zostaną zachowane.
2. Panel otworzysz z paska/menu **EnviroSolutions › GIS Assistant AI** lub skrótem **Ctrl+Alt+A**.

Wymagania: QGIS 3.34 – 4.x (Qt5 i Qt6, `supportsQt6=True`), dostęp do internetu
(lub lokalny serwer Ollama).

## Język

Wtyczka przejmuje język z ustawień QGIS (*Ustawienia › Opcje › Ogólne › Język*); nie korzysta z adresu IP
ani żadnej usługi sieciowej. Dostępne są: polski (tekst źródłowy) i angielski. Dla pozostałych języków
interfejs wtyczki jest po angielsku, ale asystent AI i tak odpowiada w języku QGIS, a ścieżki menu
podaje tak, jak wyglądają w tej wersji językowej. Zmiana języka wymaga ponownego uruchomienia QGIS.

Nowe tłumaczenie: skopiuj `i18n/gis_assistant_ai_en.ts` jako `gis_assistant_ai_<kod>.ts` (np. `de`),
ustaw atrybut `language`, przetłumacz w Qt Linguist i skompiluj poleceniem
`lrelease i18n/gis_assistant_ai_<kod>.ts` – wtyczka sama wczyta plik `.qm`.

## Konfiguracja modelu

Przycisk ustawień (ikona klucza) w nagłówku panelu:

| Dostawca | Uwagi |
|---|---|
| Anthropic Claude | domyślny; klucz API z console.anthropic.com |
| OpenAI / API zgodne z OpenAI | możliwa zmiana adresu (np. Azure, serwer firmowy) |
| Ollama | model lokalny, **żadne dane nie opuszczają komputera**, brak klucza |

Odpowiedzi modelu są odbierane strumieniowo – w linii statusu widać postęp, a długie odpowiedzi nie są
przerywane przez limit czasu sieci QGIS. Jeśli mimo to połączenie zostanie przerwane, zwiększ
*Ustawienia › Opcje › Sieć › Limit czasu*.

Jeśli klucz Anthropic nie jest przypisany do workspace (błąd HTTP 400 „not scoped to a workspace”),
wpisz w polu **ID workspace** identyfikator w formacie `wrkspc_…` z Claude Console albo utwórz
klucz w konkretnym workspace. ID workspace nie jest sekretem – zapisywane jest w ustawieniach QGIS.

Parametry zapytań (długość odpowiedzi, limit czasu) są dobrane automatycznie. Przycisk „Testuj połączenie” sprawdza konfigurację.

### Mechanizm AI (jak w Asystencie AI geoportalu MAIP)

Od wersji 0.5.0 wtyczka korzysta z modelu tak samo jak Asystent AI geoportalu:

* **Wyszukiwanie w internecie** (tylko Anthropic) – zapytanie zawiera narzędzie `web_search_20250305`
  (`WEB_SEARCH_MAX_USES` w `constants.py`). Model sam znajduje oficjalne adresy usług (GDOŚ, GUGiK, PIG-PIB…)
  i kody TERYT zamiast prosić użytkownika. Wyszukiwanie musi włączyć administrator organizacji w Claude Console
  (Settings › Privacy); po odmowie API (HTTP 400) wtyczka zapamiętuje to i ponawia zapytanie bez narzędzia.
  Opcja „Pozwól AI wyszukiwać w internecie” w ustawieniach wyłącza je całkowicie. Pole `web_search` w kontekście
  mówi modelowi, czy wyszukiwanie jest dostępne (OpenAI/Ollama – nie).
* **Cache promptu** – instrukcja systemowa jest wysyłana z `cache_control: ephemeral`, kolejne zapytania są tańsze.
* **Wznawianie tury** – przy długiej turze z wyszukiwaniem API zwraca `stop_reason: pause_turn`; wtyczka odtwarza
  bloki odpowiedzi ze strumienia (tekst, `server_tool_use`, `web_search_tool_result`) i odsyła je, żeby model
  dokończył (`LLM_MAX_CONTINUATIONS`).
* **Samodzielność** – prompt (sekcje 7–8) każe najpierw zrobić zadanie samemu (usługa, dane spod adresu, ULDK),
  pytać (`clarify`), gdy pasujące dane już są w projekcie, a `user_action` stosować w ostateczności.
  Odpowiedź na pytanie asystenta trafia do modelu jako „Wybór użytkownika … Pierwotne polecenie: …” i jest wiążąca.
* **Kontrola wyniku** – pusty wynik z niepustych danych wejściowych albo pobrane dane bez obiektów zatrzymują plan
  (sygnał `stepWarning`) z diagnozą: rozłączne zasięgi, brak zasięgu, zasięg w układzie warstwy. „Napraw z AI”
  wysyła ten opis do modelu; w kontekście są zasięgi warstw (`extent`), a w podsumowaniu kroków liczba obiektów,
  układ i zasięg warstw wynikowych. Przypisanie układu (`native:assignprojection`) niepasującego do współrzędnych
  jest blokowane.
* **Komunikaty błędów** – brak środków na koncie, niedostępny model, zbyt długi opis projektu, przeciążenie serwerów.

## Bezpieczeństwo i prywatność

* **Klucz API** jest zapisywany wyłącznie w zaszyfrowanej bazie menedżera uwierzytelniania QGIS
  (hasło główne) albo – jeśli odznaczysz zapamiętywanie – trzymany tylko w pamięci do zamknięcia
  QGIS (lub wyłączenia wtyczki). Nigdy nie trafia do pliku ustawień ani do dziennika (w komunikatach jest maskowany).
  Gdy adres API używa nieszyfrowanego `http://` (poza `localhost`), okno ustawień ostrzega i prosi o potwierdzenie.
* **Do modelu nie są wysyłane sekrety**: ze źródeł warstw usuwane są hasła, loginy, tokeny,
  klucze API, identyfikatory `authcfg` i dane logowania w adresach URL, a pełne ścieżki dysków
  są skracane do nazwy pliku. Warstwy niedostępne (np. baza bez połączenia) nie są odpytywane.
* Wysyłany jest tylko opis projektu: nazwy i typy warstw, pola, układy współrzędnych, zasięg mapy,
  lista dostawców Processing i zainstalowanych wtyczek. **Wartości atrybutów** są wysyłane
  tylko po włączeniu opcji „Wysyłaj przykładowe wartości atrybutów”.
* **Treść od modelu traktowana jest jako niezaufana.** Nazwy warstw, pól czy wartości atrybutów w cudzym
  projekcie mogą zawierać ukryte polecenia dla AI (tzw. prompt injection). Dlatego każde działanie
  o skutkach poza projektem QGIS wymaga Twojej zgody albo jest zablokowane:
  * kod PyQGIS jest **domyślnie wyłączony**; po włączeniu każdy kod jest pokazywany w całości przed
    uruchomieniem, z ostrzeżeniem o konstrukcjach wysokiego ryzyka (pliki, procesy, sieć, ustawienia
    uwierzytelniania), a przyciskiem domyślnym jest „Pomiń”;
  * wczytanie pliku z dysku lub bazy danych wskazanych przez model (a także ścieżek GDAL `/vsi…`) wymaga
    potwierdzenia; usługi sieciowe (WMS/WMTS/WFS/XYZ…) wczytywane są bez pytania;
  * otwierane są wyłącznie adresy `http(s)://` – linki `file:`, `smb:`, `ms-settings:` itp. są blokowane;
  * usługi i dane spod adresu wskazane przez model są wczytywane bez pytania tylko z adresów publicznych; adres
    w sieci wewnętrznej (localhost, 10.x, 192.168.x, *.local…) wymaga zgody, a przekierowanie do takiej sieci jest
    blokowane – dane z niej trafiłyby potem do opisu projektu wysyłanego do AI;
  * dane spod adresu: limit `MAX_DOWNLOAD_MB` (400 MB), zapis w katalogu tymczasowym Processing;
  * pola stanu kroków (np. „wykonany”) nie mogą zostać ustawione przez model.
* Wyniki algorytmów trafiają domyślnie do warstw tymczasowych – zapisz je, jeśli chcesz je zachować.

## Typy kroków planu

| Akcja | Działanie |
|---|---|
| `processing` | uruchomienie algorytmu Processing (w tle), wynik dodawany do projektu |
| `load_layer` | wczytanie warstwy WMS/WMTS, WFS, XYZ lub pliku; adres http(s) z dostawcą `ogr` – pobranie danych (GeoJSON, ZIP, GPKG, KML, GML, Overpass API → GeoPackage) |
| `add_service` | usługa WMS/WMTS/WFS/WCS: GetCapabilities, dobór warstwy po nazwie lub słowach z tytułu, dodanie do projektu |
| `uldk_boundary` | granica gminy/powiatu/województwa z usługi ULDK GUGiK (EPSG:2180) |
| `bdot10k_layer` | paczka powiatowa BDOT10k z danych otwartych GUGiK (GPKG → SHP → GML), wczytanie jednej klasy obiektów; paczka pamiętana na czas sesji |
| `user_action` | komunikat dla użytkownika i oczekiwanie na potwierdzenie (opcjonalnie wskazanie warstwy) |
| `processing_dialog` | otwarcie okna algorytmu z wypełnionymi parametrami |
| `zoom` | przybliżenie mapy do warstwy |
| `python` | krótki skrypt PyQGIS (po potwierdzeniu) |
| `note` | informacja bez działania |

Kroki odwołują się do wyników poprzednich zapisem `{{s1}}` / `{{s1.OUTPUT}}`. Identyfikatory
algorytmów są sprawdzane w rejestrze Processing i automatycznie poprawiane (np. `qgis:buffer` →
`native:buffer`).

## Serwer MCP (Claude Desktop)

Wtyczka może udostępnić QGIS aplikacji Claude Desktop jako serwer MCP (Model Context Protocol):

```
Claude Desktop ──stdio──▶ mcp_bridge.py (proces startowany przez Claude) ──HTTP 127.0.0.1:PORT──▶ QGIS: McpServer ──▶ PlanExecutor
```

| Moduł | Rola |
|---|---|
| `mcp_protocol.py` | bez Qt: parser HTTP, JSON-RPC (`initialize`, `ping`, `tools/list`, `tools/call`), katalog narzędzi ze schematami JSON i mapowanie narzędzie → krok planu |
| `mcp_server.py` | `QTcpServer` w wątku GUI (tylko `127.0.0.1`, token `Bearer`), narzędzia synchroniczne (`qgis_context`, `layer_info`, `list_algorithms`, `algorithm_help`, `set_layer_style`) i asynchroniczne przez własny `PlanExecutor` (`run_processing`, `load_layer`, `add_service`, `uldk_boundary`, `bdot10k_layer`, `zoom_to_layer`, `run_plan`); jedno wywołanie naraz, limit 20 min |
| `mcp_bridge.py` | samodzielny skrypt (tylko biblioteka standardowa) uruchamiany przez Claude Desktop; przekazuje JSON-RPC ze stdin do serwera w QGIS; gdy QGIS nie odpowiada, sam odpowiada na `initialize` i zwraca narzędzie `qgis_status` z instrukcją |

Włączenie: Ustawienia wtyczki › „Serwer MCP (Claude Desktop)” › zaznacz, zapisz, „Skopiuj konfigurację Claude Desktop”
→ wklej do `claude_desktop_config.json` (Claude Desktop: Settings › Developer › Edit Config) → uruchom Claude Desktop
ponownie. Token przechowywany jest w ustawieniach QGIS (`mcp/token`) i w konfiguracji Claude Desktop; przycisk
„Nowy token” unieważnia stary. Zasady bezpieczeństwa executora obowiązują: kroki `user_action`, `python`,
`processing_dialog` nie są dostępne; adresy w sieci wewnętrznej wymagają `allow_internal_network=true` w wywołaniu.
Każde wywołanie jest logowane w dzienniku QGIS (zakładka GIS Assistant AI).
Opisy narzędzi, instrukcje serwera i komunikaty mostu są po polsku, gdy język interfejsu QGIS to polski, w każdym innym
przypadku po angielsku (`mcp_protocol._EN`, `mcp_server.INSTRUCTIONS`, `mcp_bridge.TEXTS`; most dostaje `--lang` w konfiguracji).

Test ręczny bez Claude: `curl -X POST http://127.0.0.1:8765/mcp -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`

## Budowa

```
gis_assistant_ai/
├── plugin.py            – rejestracja w pasku i menu „EnviroSolutions”, panel
├── ui/dock.py           – panel: polecenie, wynik, WYKONAJ, akcje użytkownika, błędy, dziennik
├── ui/render.py         – widok HTML planu/narzędzi
├── ui/styles.py         – paleta z księgi znaku, jasny i ciemny motyw
├── ui/widgets.py        – zwijane sekcje (Polecenie, Wynik, Dziennik), ui/icons.py – ikony SVG
├── ui/settings_dialog.py
├── ui/confirm_dialog.py – zatwierdzanie kodu PyQGIS i wczytania lokalnych danych
├── llm_client.py        – asynchroniczne zapytania (QgsNetworkAccessManager, obsługa proxy QGIS)
├── prompts.py           – instrukcja systemowa i format odpowiedzi JSON
├── context_builder.py   – opis projektu (z usuwaniem sekretów)
├── plan_model.py        – parsowanie i walidacja odpowiedzi
├── executor.py          – wykonywanie planu krok po kroku, kontrola wyników
├── services.py          – GetCapabilities, dobór warstw usług, dane spod adresu, Overpass (bez zależności od QGIS)
├── settings.py          – ustawienia i bezpieczne przechowywanie klucza
├── i18n.py, i18n/       – wybór języka wg QGIS i pliki tłumaczeń (.ts/.qm)
└── utils.py
```

Poza katalogiem wtyczki (nie trafiają do ZIP-a):

```
tests/                   – testy (pytest); część z QGIS pomijana, gdy nie da się zaimportować qgis
scripts/package.py       – buduje dist/gis_assistant_ai-<wersja>.zip
docs/                    – materiały do README (animacja z przykładem użycia)
.github/workflows/       – testy w QGIS 3.40/LTR/stable/latest, zgodność Qt5/Qt6, flake8 + Bandit + detect-secrets, wydanie
```

## Rozwój

* Standard kodu: PEP 8, linie do 79 znaków, docstringi (PEP 257):
  `flake8 .` (konfiguracja w `setup.cfg`; wymaga `pip install flake8 flake8-docstrings pep8-naming`).
  Wyjątek: treść instrukcji dla modelu w `prompts.py` nie jest łamana do 79 znaków (E501), żeby dało się ją czytać
  i edytować jako jeden tekst.
* Testy: w katalogu repozytorium `pytest`. Moduły niezależne od QGIS (`utils`, `plan_model`, `services`,
  `stream`, `mcp_protocol`, `mcp_bridge`) testowane są zawsze; testy wymagające QGIS (kontekst projektu,
  executor) uruchamiają się, gdy Python widzi pakiet `qgis` – w CI w obrazach `qgis/qgis`.
* Tłumaczenia: `i18n/gis_assistant_ai_en.ts` (Qt Linguist) → `lrelease`. Tekst przekazywany do `tr()` jest
  kluczem tłumaczenia – zmiana treści wymaga aktualizacji `.ts` i ponownej kompilacji `.qm`.
* Nowa wersja: podnieś `version=` w `metadata.txt`, dopisz wpis na początku `changelog=`, zbuduj ZIP
  (`python scripts/package.py`), a po wypchnięciu zmian utwórz tag `v<wersja>` – workflow *Release*
  sprawdzi zgodność tagu z `metadata.txt` i opublikuje ZIP w wydaniu na GitHubie.

## Do uzupełnienia

* Lista modeli w `constants.py` – aktualizuj według bieżącej oferty dostawców.

## Licencja

GNU GPL v3 – © 2026 EnviroSolutions Sp. z o.o.

---
Instrukcja dla użytkowników: [README.md](README.md).
