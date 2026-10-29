<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US" sourcelanguage="pl_PL">
<context>
    <name>GISAssistantAI</name>
    <message>
        <location filename="../ui/dock.py" line="524"/>
        <source> (w tym %d wymagające Twojej akcji)</source>
        <translation> (%d requiring your action)</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="299"/>
        <source> – brak połączenia z serwerem (sieć/proxy/adres API).</source>
        <translation> – cannot reach the server (network/proxy/API address).</translation>
    </message>
    <message>
        <location filename="../plugin.py" line="42"/>
        <source> – opisz, co chcesz zrobić w QGIS</source>
        <translation> – describe what you want to do in QGIS</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="292"/>
        <source> – przekroczony limit zapytań, spróbuj za chwilę.</source>
        <translation> – rate limit exceeded, try again in a moment.</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="295"/>
        <source> – serwer nie odpowiedział w wyznaczonym czasie (%d s). Spróbuj ponownie lub wybierz szybszy model; limit czasu sieci można też zwiększyć w Ustawienia › Opcje › Sieć.</source>
        <translation> – the server did not respond in time (%d s). Try again or choose a faster model; the network timeout can also be increased in Settings › Options › Network.</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="287"/>
        <source> – sprawdź klucz API w ustawieniach.</source>
        <translation> – check the API key in the settings.</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="289"/>
        <source> – ten klucz nie jest przypisany do workspace. Wpisz ID workspace (wrkspc_…) w ustawieniach wtyczki albo utwórz w Claude Console klucz przypisany do workspace.</source>
        <translation> – this key is not scoped to a workspace. Enter the workspace ID (wrkspc_…) in the plugin settings or create a workspace-scoped key in the Claude Console.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="22"/>
        <source> – ustawienia</source>
        <translation> – settings</translation>
    </message>
    <message>
        <location filename="../executor.py" line="535"/>
        <source>%s: %d obiekt(y)</source>
        <translation>%s: %d feature(s)</translation>
    </message>
    <message>
        <location filename="../executor.py" line="422"/>
        <source>%s: %d obiektów</source>
        <translation>%s: %d features</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="895"/>
        <source>(odebrano znaków: %d)</source>
        <translation>(characters received: %d)</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="608"/>
        <source>AI nie zaproponowało poprawionych kroków.</source>
        <translation>The AI did not propose corrected steps.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="605"/>
        <source>AI potwierdziło, że dalsze kroki nie wymagają zmian.</source>
        <translation>The AI confirmed that the remaining steps need no changes.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="115"/>
        <source>ALGORYTM</source>
        <translation>ALGORITHM</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="67"/>
        <source>ASYSTENT PRACUJE</source>
        <translation>ASSISTANT AT WORK</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="210"/>
        <source>Adres API używa nieszyfrowanego połączenia http://, więc klucz API może zostać przechwycony. Zapisać mimo to?</source>
        <translation>The API address uses an unencrypted http:// connection, so the API key could be intercepted. Save anyway?</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="60"/>
        <source>Adres API:</source>
        <translation>API address:</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="172"/>
        <source>Adres nie używa szyfrowania (http://) – klucz API zostałby wysłany jawnym tekstem. Użyj https://.</source>
        <translation>The address is not encrypted (http://) – the API key would be sent as plain text. Use https://.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="384"/>
        <source>Algorytm zakończył się niepowodzeniem.</source>
        <translation>The algorithm failed.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="709"/>
        <source>Algorytm „%s” jest niedostępny – wtyczka dostarczająca algorytmy „%s” nie jest zainstalowana lub włączona.</source>
        <translation>Algorithm “%s” is not available – the plugin providing the “%s” algorithms is not installed or enabled.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="714"/>
        <source>Algorytm „%s” jest niedostępny.</source>
        <translation>Algorithm “%s” is not available.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="712"/>
        <source>Algorytm „%s” jest niedostępny. Dostępne algorytmy dostawcy „%s”: %s.</source>
        <translation>Algorithm “%s” is not available. Algorithms available from provider “%s”: %s.</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="141"/>
        <source>Algorytm „%s” nie jest dostępny w tej instalacji QGIS.</source>
        <translation>Algorithm “%s” is not available in this QGIS installation.</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="139"/>
        <source>Algorytm „%s” pochodzi z wtyczki, która nie jest zainstalowana lub włączona (dostawca Processing „%s”).</source>
        <translation>Algorithm “%s” comes from a plugin that is not installed or enabled (Processing provider “%s”).</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="125"/>
        <source>Analizuj</source>
        <translation>Analyze</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="575"/>
        <source>Analizuję błąd i poprawiam plan…</source>
        <translation>Analyzing the error and correcting the plan…</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="479"/>
        <source>Analizuję polecenie i projekt…</source>
        <translation>Analyzing the request and the project…</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="67"/>
        <source>Analizuję polecenie…</source>
        <translation>Analyzing the request…</translation>
    </message>
    <message>
        <location filename="../constants.py" line="31"/>
        <source>Anthropic Claude</source>
        <translation>Anthropic Claude</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="362"/>
        <source>Asystent przeanalizuje błąd i poprawi pozostałe kroki planu</source>
        <translation>The assistant will analyze the error and correct the remaining steps</translation>
    </message>
    <message>
        <location filename="../executor.py" line="468"/>
        <source>Brak adresu (uri) warstwy.</source>
        <translation>Layer address (uri) is missing.</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="118"/>
        <source>Brak identyfikatora algorytmu.</source>
        <translation>Algorithm ID is missing.</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="77"/>
        <source>Brak klucza API – uzupełnij go w ustawieniach wtyczki (ikona ⚙).</source>
        <translation>No API key – add it in the plugin settings.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="515"/>
        <source>Brak kodu TERYT jednostki.</source>
        <translation>The TERYT code of the unit is missing.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="73"/>
        <source>BŁĄD</source>
        <translation>ERROR</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="300"/>
        <location filename="../llm_client.py" line="247"/>
        <source>Błąd API%s: %s%s</source>
        <translation>API error%s: %s%s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="559"/>
        <source>Błąd połączenia z ULDK: %s</source>
        <translation>ULDK connection error: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="287"/>
        <source>Błąd w kroku „%s”: %s</source>
        <translation>Error in step “%s”: %s</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="73"/>
        <source>Coś poszło nie tak</source>
        <translation>Something went wrong</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="690"/>
        <source>Czekam na Twoją akcję…</source>
        <translation>Waiting for your action…</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="98"/>
        <source>Do modelu wysyłane są: treść polecenia oraz opis projektu (nazwy i pola warstw, układy współrzędnych, zasięg mapy). Hasła, loginy, tokeny i pełne ścieżki dysków są usuwane. Wybierając Ollama, wszystko pozostaje na Twoim komputerze.</source>
        <translation>The model receives your request and a description of the project (layer names and fields, coordinate systems, map extent). Passwords, logins, tokens and full disk paths are removed. With Ollama everything stays on your computer.</translation>
    </message>
    <message>
        <location filename="../constants.py" line="71"/>
        <source>Dodaj ortofotomapę z Geoportalu jako podkład mapowy</source>
        <translation>Add the Geoportal orthophoto map as a basemap</translation>
    </message>
    <message>
        <location filename="../executor.py" line="424"/>
        <source>Dodano warstwę %s</source>
        <translation>Added layer %s</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="55"/>
        <source>Domyślny</source>
        <translation>Default</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="569"/>
        <source>Dopasowuję dalsze kroki do wczytanych danych…</source>
        <translation>Adapting the next steps to the loaded data…</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="42"/>
        <source>Dostawca:</source>
        <translation>Provider:</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="192"/>
        <source>Dziennik</source>
        <translation>Log</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="122"/>
        <source>Enter – wyślij, Shift+Enter – nowa linia</source>
        <translation>Enter – send, Shift+Enter – new line</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="78"/>
        <source>Fragment odpowiedzi modelu:</source>
        <translation>Part of the model response:</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="49"/>
        <source>Gdy potrzebna będzie Twoja decyzja (np. podłączenie usługi WMS), plan zatrzyma się i poczeka na potwierdzenie.</source>
        <translation>When your decision is needed (e.g. connecting a WMS service), the plan pauses and waits for your confirmation.</translation>
    </message>
    <message>
        <location filename="../constants.py" line="73"/>
        <source>Gdzie znajdę narzędzie do agregacji (rozpuszczania) poligonów?</source>
        <translation>Where do I find the tool for dissolving polygons?</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="114"/>
        <source>Gotowe polecenia do wypróbowania</source>
        <translation>Ready-made requests to try</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="84"/>
        <source>ID workspace:</source>
        <translation>Workspace ID:</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="14"/>
        <source>INFORMACJA</source>
        <translation>INFO</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="52"/>
        <source>JAK TO DZIAŁA</source>
        <translation>HOW IT WORKS</translation>
    </message>
    <message>
        <location filename="../constants.py" line="74"/>
        <source>Jak wyszukać działkę ewidencyjną po numerze?</source>
        <translation>How do I find a cadastral parcel by its number?</translation>
    </message>
    <message>
        <location filename="../constants.py" line="72"/>
        <source>Jakim narzędziem połączę kilka warstw wektorowych w jedną?</source>
        <translation>Which tool merges several vector layers into one?</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="13"/>
        <source>KOD PYQGIS</source>
        <translation>PYQGIS CODE</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="866"/>
        <source>Klucz API zapisany: %s.</source>
        <translation>API key saved: %s.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="75"/>
        <source>Klucz API:</source>
        <translation>API key:</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="157"/>
        <source>Klucz jest wysyłany wyłącznie w nagłówku zapytania do powyższego adresu API. Nie jest zapisywany jawnym tekstem w profilu QGIS.</source>
        <translation>The key is sent only in the request header to the API address above. It is never stored as plain text in the QGIS profile.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="78"/>
        <source>Klucz trafia do zaszyfrowanej bazy menedżera uwierzytelniania QGIS. Bez zaznaczenia jest pamiętany tylko do zamknięcia QGIS.</source>
        <translation>The key is stored in the encrypted QGIS authentication database. When unchecked, it is kept only until QGIS closes.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="180"/>
        <source>Klucz usunięty.</source>
        <translation>Key removed.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="751"/>
        <source>Kod Python jest wyłączony w ustawieniach – krok pominięty.</source>
        <translation>Python code is disabled in the settings – step skipped.</translation>
    </message>
    <message>
        <location filename="../ui/confirm_dialog.py" line="23"/>
        <source>Kod zawiera konstrukcje o skutkach poza projektem QGIS: %s. Zatwierdź tylko, jeśli rozumiesz, co robi.</source>
        <translation>The code contains constructs with effects outside the QGIS project: %s. Approve only if you understand what it does.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="544"/>
        <source>Korekta przez AI nie powiodła się: %s</source>
        <translation>AI correction failed: %s</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="85"/>
        <source>Krok %d</source>
        <translation>Step %d</translation>
    </message>
    <message>
        <location filename="../executor.py" line="263"/>
        <source>Krok %d: %s</source>
        <translation>Step %d: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="763"/>
        <source>Krok „%s” chce wczytać do projektu plik lub bazę danych wskazane przez AI. Zatwierdź tylko, jeśli znasz to źródło.</source>
        <translation>Step “%s” wants to load a file or database chosen by the AI into the project. Approve only if you know this source.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="756"/>
        <source>Krok „%s” chce wykonać poniższy kod Python. Sprawdź go przed zatwierdzeniem.</source>
        <translation>Step “%s” wants to run the Python code below. Review it before approving.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="293"/>
        <source>Krok „%s” nie ma jeszcze wyniku (pominięty lub nie wykonany).</source>
        <translation>Step “%s” has no result yet (skipped or not run).</translation>
    </message>
    <message>
        <location filename="../executor.py" line="297"/>
        <source>Krok „%s” nie ma wyjścia „%s” (dostępne: %s).</source>
        <translation>Step “%s” has no output “%s” (available: %s).</translation>
    </message>
    <message>
        <location filename="../executor.py" line="305"/>
        <source>Krok „%s” nie zwrócił warstwy.</source>
        <translation>Step “%s” did not return a layer.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="142"/>
        <source>Lista modeli</source>
        <translation>Model list</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="12"/>
        <source>MAPA</source>
        <translation>MAP</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="115"/>
        <source>MENU</source>
        <translation>MENU</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="95"/>
        <source>Maks. 5 wartości tekstowych na pole – model trafniej buduje wyrażenia filtrujące.</source>
        <translation>Up to 5 text values per field – helps the model build accurate filter expressions.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="318"/>
        <source>Menedżer źródeł danych</source>
        <translation>Data Source Manager</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="118"/>
        <source>Menu</source>
        <translation>Menu</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="36"/>
        <source>Model językowy</source>
        <translation>Language model</translation>
    </message>
    <message>
        <location filename="../utils.py" line="14"/>
        <source>Model zwrócił pustą odpowiedź.</source>
        <translation>The model returned an empty response.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="62"/>
        <location filename="../ui/settings_dialog.py" line="51"/>
        <source>Model:</source>
        <translation>Model:</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="106"/>
        <source>NARZĘDZIE</source>
        <translation>TOOL</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="448"/>
        <source>Najpierw podaj klucz API w ustawieniach.</source>
        <translation>Enter the API key in the settings first.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="360"/>
        <source>Napraw z AI</source>
        <translation>Fix with AI</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="108"/>
        <source>Narzędzie</source>
        <translation>Tool</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="849"/>
        <source>Nie można otworzyć %s: %s</source>
        <translation>Cannot open %s: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="390"/>
        <source>Nie udało się dodać wyników do projektu: %s</source>
        <translation>Could not add the results to the project: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="541"/>
        <source>Nie udało się dopasować planu – kontynuuję bez zmian.</source>
        <translation>Could not adapt the plan – continuing unchanged.</translation>
    </message>
    <message>
        <location filename="../settings.py" line="133"/>
        <source>Nie udało się odczytać klucza API: %s</source>
        <translation>Could not read the API key: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="597"/>
        <source>Nie udało się odczytać korekty planu: %s</source>
        <translation>Could not read the plan correction: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="601"/>
        <source>Nie udało się odczytać korekty: %s</source>
        <translation>Could not read the correction: %s</translation>
    </message>
    <message>
        <location filename="../utils.py" line="29"/>
        <source>Nie udało się odczytać odpowiedzi modelu jako JSON.</source>
        <translation>Could not read the model response as JSON.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="507"/>
        <source>Nie udało się odczytać odpowiedzi: %s</source>
        <translation>Could not read the response: %s</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="82"/>
        <source>Nie udało się przygotować zapytania: %s</source>
        <translation>Could not prepare the request: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="539"/>
        <source>Nie udało się uzyskać odpowiedzi.</source>
        <translation>Could not get a response.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="487"/>
        <source>Nie udało się wczytać warstwy (%s). %s
Możesz wczytać ją ręcznie i pominąć ten krok albo poprosić AI o poprawkę.</source>
        <translation>Could not load the layer (%s). %s
You can load it manually and skip this step, or ask the AI for a fix.</translation>
    </message>
    <message>
        <location filename="../settings.py" line="154"/>
        <source>Nie udało się zapisać klucza API: %s</source>
        <translation>Could not save the API key: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="188"/>
        <source>Nie wskazano warstwy – kolejne kroki mogą jej wymagać.</source>
        <translation>No layer selected – the next steps may need one.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="730"/>
        <source>Nie wskazano warstwy. Kolejne kroki mogą jej potrzebować. Kontynuować?</source>
        <translation>No layer selected. The next steps may need one. Continue?</translation>
    </message>
    <message>
        <location filename="../executor.py" line="608"/>
        <source>Nie znaleziono warstwy do przybliżenia.</source>
        <translation>No layer found to zoom to.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="484"/>
        <source>Nieobsługiwany dostawca danych „%s”.</source>
        <translation>Unsupported data provider “%s”.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="267"/>
        <source>Nieobsługiwany typ kroku: %s</source>
        <translation>Unsupported step type: %s</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="252"/>
        <source>Nieoczekiwany format odpowiedzi API: %s</source>
        <translation>Unexpected API response format: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="341"/>
        <source>Niepoprawne parametry: %s
Parametry: %s</source>
        <translation>Invalid parameters: %s
Parameters: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="511"/>
        <source>Nieznany poziom jednostki ULDK: %s</source>
        <translation>Unknown ULDK unit level: %s</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="75"/>
        <source>Nieznany typ kroku „%s” – potraktowano jako informację.</source>
        <translation>Unknown step type “%s” – treated as information.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="260"/>
        <source>Nowe polecenie</source>
        <translation>New request</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="879"/>
        <source>Nowe polecenie.</source>
        <translation>New request.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="460"/>
        <source>Nowe warstwy: %d</source>
        <translation>New layers: %d</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="86"/>
        <source>ODPOWIEDŹ</source>
        <translation>ANSWER</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="8"/>
        <source>OKNO NARZĘDZIA</source>
        <translation>TOOL DIALOG</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="101"/>
        <source>Odpowiedz w polu poleceń lub kliknij opcję.</source>
        <translation>Reply in the request box or click an option.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="86"/>
        <source>Odpowiedź</source>
        <translation>Answer</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="528"/>
        <source>Odpowiedź gotowa.</source>
        <translation>Answer ready.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="509"/>
        <source>Odpowiedź modelu była niepoprawna.</source>
        <translation>The model response was invalid.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="640"/>
        <source>Odrzucono wykonanie kodu Python – krok pominięty.</source>
        <translation>Python code rejected – step skipped.</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="155"/>
        <source>Odwołanie do nieznanego kroku: %s.</source>
        <translation>Reference to an unknown step: %s.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="454"/>
        <source>Okno zamknięte bez uruchomienia – krok pominięty.</source>
        <translation>Dialog closed without running – step skipped.</translation>
    </message>
    <message>
        <location filename="../constants.py" line="45"/>
        <source>Ollama (lokalnie – dane nie opuszczają komputera)</source>
        <translation>Ollama (local – data stays on your computer)</translation>
    </message>
    <message>
        <location filename="../constants.py" line="38"/>
        <source>OpenAI / API zgodne z OpenAI</source>
        <translation>OpenAI / OpenAI-compatible API</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="99"/>
        <source>Opisz, co chcesz zrobić w QGIS…
np. „Stwórz bufor o promieniu 100 m od szkół w powiecie piaseczyńskim”</source>
        <translation>Describe what you want to do in QGIS…
e.g. “Create a 100 m buffer around schools in Piaseczno County”</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="319"/>
        <source>Otwórz narzędzie</source>
        <translation>Open tool</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="231"/>
        <source>PLAN DZIAŁAŃ · %d KROK</source>
        <translation>ACTION PLAN · %d STEP</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="233"/>
        <source>PLAN DZIAŁAŃ · %d KROKI</source>
        <translation>ACTION PLAN · %d STEPS</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="234"/>
        <source>PLAN DZIAŁAŃ · %d KROKÓW</source>
        <translation>ACTION PLAN · %d STEPS</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="7"/>
        <source>PROCESSING</source>
        <translation>PROCESSING</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="92"/>
        <source>PYTANIE</source>
        <translation>QUESTION</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="611"/>
        <source>Plan dopasowany do danych.</source>
        <translation>Plan adapted to the data.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="154"/>
        <source>Plan działań</source>
        <translation>Action plan</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="525"/>
        <source>Plan gotowy: %d krok(ów)%s. Sprawdź go i kliknij WYKONAJ.</source>
        <translation>Plan ready: %d step(s)%s. Review it and click RUN.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="611"/>
        <source>Plan poprawiony.</source>
        <translation>Plan corrected.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="257"/>
        <source>Plan wykonany.</source>
        <translation>Plan completed.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="218"/>
        <source>Plan zaktualizowany (%d nowych kroków).</source>
        <translation>Plan updated (%d new steps).</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="659"/>
        <source>Plan „%s” został wykonany.</source>
        <translation>Plan “%s” completed.</translation>
    </message>
    <message>
        <location filename="../constants.py" line="70"/>
        <source>Pobierz granicę gminy Lesznowola i policz jej powierzchnię w hektarach</source>
        <translation>Get the boundary of Lesznowola municipality and calculate its area in hectares</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="95"/>
        <source>Polecenie</source>
        <translation>Request</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="480"/>
        <source>Polecenie: %s</source>
        <translation>Request: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="362"/>
        <source>Pomijam nieznany parametr „%s” algorytmu %s.</source>
        <translation>Skipping unknown parameter “%s” of algorithm %s.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="200"/>
        <location filename="../executor.py" line="456"/>
        <location filename="../executor.py" line="499"/>
        <source>Pominięto krok: %s</source>
        <translation>Step skipped: %s</translation>
    </message>
    <message>
        <location filename="../ui/confirm_dialog.py" line="37"/>
        <location filename="../ui/dock.py" line="367"/>
        <source>Pomiń</source>
        <translation>Skip</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="333"/>
        <source>Pomiń krok</source>
        <translation>Skip step</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="364"/>
        <source>Ponów</source>
        <translation>Retry</translation>
    </message>
    <message>
        <location filename="../plan_model.py" line="123"/>
        <location filename="../plan_model.py" line="132"/>
        <location filename="../plan_model.py" line="137"/>
        <source>Poprawiono identyfikator %s → %s.</source>
        <translation>Corrected ID %s → %s.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="92"/>
        <source>Potrzebuję doprecyzowania</source>
        <translation>I need more details</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="529"/>
        <source>Potrzebuję doprecyzowania.</source>
        <translation>I need more details.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="255"/>
        <source>Powiedz, co chcesz zrobić w QGIS</source>
        <translation>Tell me what you want to do in QGIS</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="96"/>
        <source>Pozwól AI proponować kod PyQGIS (zawsze po Twoim zatwierdzeniu)</source>
        <translation>Allow the AI to propose PyQGIS code (always after your approval)</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="106"/>
        <source>Proponowane narzędzie</source>
        <translation>Suggested tool</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="91"/>
        <source>Prywatność i bezpieczeństwo</source>
        <translation>Privacy and security</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="336"/>
        <location filename="../ui/dock.py" line="370"/>
        <source>Przerwij</source>
        <translation>Abort</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="118"/>
        <source>Przybornik</source>
        <translation>Toolbox</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="109"/>
        <source>Przykłady</source>
        <translation>Examples</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="167"/>
        <source>Rezultat:</source>
        <translation>Result:</translation>
    </message>
    <message>
        <location filename="../executor.py" line="151"/>
        <source>Rozpoczynam wykonywanie planu „%s”.</source>
        <translation>Starting plan “%s”.</translation>
    </message>
    <message>
        <location filename="../ui/widgets.py" line="78"/>
        <source>Rozwiń sekcję</source>
        <translation>Expand section</translation>
    </message>
    <message>
        <location filename="../constants.py" line="24"/>
        <source>SYSTEMY I WSPARCIE GIS</source>
        <translation>GIS SYSTEMS &amp; SUPPORT</translation>
    </message>
    <message>
        <location filename="../constants.py" line="25"/>
        <source>SZKOLENIA GIS</source>
        <translation>GIS TRAINING</translation>
    </message>
    <message>
        <location filename="../constants.py" line="69"/>
        <source>Stwórz bufor o promieniu 100 metrów od szkół w powiecie piaseczyńskim</source>
        <translation>Create a 100 m buffer around schools in Piaseczno County</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="155"/>
        <source>Szczegóły techniczne</source>
        <translation>Technical details</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="11"/>
        <source>TWOJA AKCJA</source>
        <translation>YOUR ACTION</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="621"/>
        <source>Ten plan był już wykonywany. Wykonać go ponownie od początku?</source>
        <translation>This plan has already been run. Run it again from the start?</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="109"/>
        <source>Testuj połączenie</source>
        <translation>Test connection</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="462"/>
        <source>Trwa wykonywanie planu – zatrzymaj je, aby zadać nowe pytanie.</source>
        <translation>A plan is running – stop it to ask a new question.</translation>
    </message>
    <message>
        <location filename="../executor.py" line="566"/>
        <source>ULDK nie znalazło jednostki o kodzie „%s” (%s). Odpowiedź: %s</source>
        <translation>ULDK found no unit with code “%s” (%s). Response: %s</translation>
    </message>
    <message>
        <location filename="../executor.py" line="531"/>
        <source>ULDK nie zwróciło żadnej geometrii.</source>
        <translation>ULDK returned no geometry.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="261"/>
        <source>Ustawienia</source>
        <translation>Settings</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="70"/>
        <source>Usuń klucz</source>
        <translation>Remove key</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="9"/>
        <source>WCZYTANIE WARSTWY</source>
        <translation>LOAD LAYER</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="115"/>
        <source>WTYCZKA</source>
        <translation>PLUGIN</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="177"/>
        <location filename="../ui/dock.py" line="475"/>
        <location filename="../ui/dock.py" line="638"/>
        <source>WYKONAJ</source>
        <translation>RUN</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="638"/>
        <source>WYKONYWANIE…</source>
        <translation>RUNNING…</translation>
    </message>
    <message>
        <location filename="../executor.py" line="612"/>
        <source>Warstwa jest pusta – brak zasięgu do przybliżenia.</source>
        <translation>The layer is empty – no extent to zoom to.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="679"/>
        <source>Warstwa%s:</source>
        <translation>Layer%s:</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="306"/>
        <source>Warstwa:</source>
        <translation>Layer:</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="765"/>
        <source>Wczytaj</source>
        <translation>Load</translation>
    </message>
    <message>
        <location filename="../executor.py" line="491"/>
        <source>Wczytano: %s</source>
        <translation>Loaded: %s</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="52"/>
        <source>Witaj w GIS Assistant AI</source>
        <translation>Welcome to GIS Assistant AI</translation>
    </message>
    <message>
        <location filename="../executor.py" line="186"/>
        <source>Wskazana warstwa: %s</source>
        <translation>Selected layer: %s</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="49"/>
        <source>Współpracuj</source>
        <translation>Work together</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="746"/>
        <source>Wybierz, co zrobić z błędem.</source>
        <translation>Choose how to handle the error.</translation>
    </message>
    <message>
        <location filename="../ui/confirm_dialog.py" line="41"/>
        <source>Wykonaj</source>
        <translation>Run</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="757"/>
        <source>Wykonaj kod</source>
        <translation>Run code</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="181"/>
        <source>Wykonaj plan działań krok po kroku</source>
        <translation>Run the action plan step by step</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="330"/>
        <source>Wykonałem – kontynuuj</source>
        <translation>Done – continue</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="643"/>
        <location filename="../ui/dock.py" line="500"/>
        <source>Wykonuję plan…</source>
        <translation>Running the plan…</translation>
    </message>
    <message>
        <location filename="../executor.py" line="171"/>
        <source>Wykonywanie planu przerwane przez użytkownika.</source>
        <translation>Plan stopped by the user.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="662"/>
        <source>Wykonywanie przerwane.</source>
        <translation>Run stopped.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="152"/>
        <source>Wynik</source>
        <translation>Result</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="93"/>
        <source>Wysyłaj przykładowe wartości atrybutów</source>
        <translation>Send sample attribute values</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="830"/>
        <source>Zablokowano otwarcie adresu spoza http(s): %s</source>
        <translation>Blocked opening a non-http(s) address: %s</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="142"/>
        <source>Zainstaluj w Menedżerze wtyczek</source>
        <translation>Install in the Plugin Manager</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="77"/>
        <source>Zapamiętaj klucz (zaszyfrowany w QGIS)</source>
        <translation>Remember key (encrypted in QGIS)</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="45"/>
        <source>Zapytaj o narzędzie</source>
        <translation>Ask about a tool</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="184"/>
        <source>Zatrzymaj</source>
        <translation>Stop</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="157"/>
        <source>Założenia:</source>
        <translation>Assumptions:</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="47"/>
        <source>Zleć zadanie</source>
        <translation>Delegate a task</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="528"/>
        <source>Znalazłem narzędzie.</source>
        <translation>Tool found.</translation>
    </message>
    <message>
        <location filename="../ui/widgets.py" line="78"/>
        <source>Zwiń sekcję</source>
        <translation>Collapse section</translation>
    </message>
    <message>
        <location filename="../utils.py" line="223"/>
        <source>dynamiczne wykonanie kodu</source>
        <translation>dynamic code execution</translation>
    </message>
    <message>
        <location filename="../utils.py" line="225"/>
        <source>introspekcja interpretera</source>
        <translation>interpreter introspection</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="755"/>
        <source>kod PyQGIS</source>
        <translation>PyQGIS code</translation>
    </message>
    <message>
        <location filename="../llm_client.py" line="314"/>
        <source>nieznany dostawca</source>
        <translation>unknown provider</translation>
    </message>
    <message>
        <location filename="../utils.py" line="221"/>
        <source>odczyt/zapis plików (open)</source>
        <translation>reading/writing files (open)</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="83"/>
        <source>opcjonalnie, np. wrkspc_01AbCd… – wymagane dla kluczy bez workspace</source>
        <translation>optional, e.g. wrkspc_01AbCd… – required for keys without a workspace</translation>
    </message>
    <message>
        <location filename="../utils.py" line="220"/>
        <source>operacje na plikach</source>
        <translation>file operations</translation>
    </message>
    <message>
        <location filename="../utils.py" line="222"/>
        <source>połączenia sieciowe</source>
        <translation>network connections</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="60"/>
        <source>skonfiguruj klucz API</source>
        <translation>configure the API key</translation>
    </message>
    <message>
        <location filename="../utils.py" line="218"/>
        <source>system operacyjny (os)</source>
        <translation>operating system (os)</translation>
    </message>
    <message>
        <location filename="../settings.py" line="144"/>
        <source>tylko w pamięci (do zamknięcia QGIS)</source>
        <translation>in memory only (until QGIS closes)</translation>
    </message>
    <message>
        <location filename="../settings.py" line="147"/>
        <source>tylko w pamięci – menedżer uwierzytelniania QGIS jest niedostępny</source>
        <translation>in memory only – the QGIS authentication manager is unavailable</translation>
    </message>
    <message>
        <location filename="../settings.py" line="150"/>
        <source>tylko w pamięci – nie podano hasła głównego QGIS</source>
        <translation>in memory only – the QGIS master password was not entered</translation>
    </message>
    <message>
        <location filename="../settings.py" line="155"/>
        <source>tylko w pamięci – zapis w menedżerze uwierzytelniania nie powiódł się</source>
        <translation>in memory only – saving to the authentication manager failed</translation>
    </message>
    <message>
        <location filename="../utils.py" line="219"/>
        <source>uruchamianie programów</source>
        <translation>running programs</translation>
    </message>
    <message>
        <location filename="../utils.py" line="226"/>
        <source>usuwanie danych</source>
        <translation>deleting data</translation>
    </message>
    <message>
        <location filename="../utils.py" line="224"/>
        <source>uwierzytelnianie i ustawienia QGIS</source>
        <translation>QGIS authentication and settings</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="762"/>
        <source>wczytanie danych</source>
        <translation>loading data</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="154"/>
        <source>wklej klucz API</source>
        <translation>paste the API key</translation>
    </message>
    <message>
        <location filename="../executor.py" line="440"/>
        <source>wynik</source>
        <translation>result</translation>
    </message>
    <message>
        <location filename="../settings.py" line="152"/>
        <source>zaszyfrowany w menedżerze uwierzytelniania QGIS</source>
        <translation>encrypted in the QGIS authentication manager</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="192"/>
        <source>Łączę…</source>
        <translation>Connecting…</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="309"/>
        <source>— wskaż warstwę —</source>
        <translation>— select a layer —</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="45"/>
        <source>„Jakim narzędziem połączę kilka warstw w jedną?” – dostaniesz nazwę, ścieżkę w menu i przycisk otwierający narzędzie.</source>
        <translation>“Which tool merges several layers into one?” – you get the name, the menu path and a button that opens the tool.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="47"/>
        <source>„Stwórz bufor 100 m od szkół w powiecie piaseczyńskim” – dostaniesz plan krok po kroku; kliknij &lt;b&gt;WYKONAJ&lt;/b&gt;, a wtyczka go zrealizuje.</source>
        <translation>“Create a 100 m buffer around schools in Piaseczno County” – you get a step-by-step plan; click &lt;b&gt;RUN&lt;/b&gt; and the plugin carries it out.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="154"/>
        <source>•••••••• (klucz zapisany – wpisz nowy, aby zmienić)</source>
        <translation>•••••••• (key saved – type a new one to change it)</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="317"/>
        <location filename="../ui/render.py" line="137"/>
        <source>↗ Strona wtyczki</source>
        <translation>↗ Plugin page</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="80"/>
        <source>↻ Spróbuj ponownie</source>
        <translation>↻ Try again</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="133"/>
        <source>▶ Menedżer źródeł danych</source>
        <translation>▶ Data Source Manager</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="129"/>
        <source>▶ Otwórz narzędzie</source>
        <translation>▶ Open tool</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="672"/>
        <source>✋  Krok %d wymaga Twojej akcji: %s</source>
        <translation>✋  Step %d needs your action: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="658"/>
        <source>✔ Plan wykonany.</source>
        <translation>✔ Plan completed.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py" line="199"/>
        <source>✔ Połączenie działa.</source>
        <translation>✔ Connection works.</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="58"/>
        <source>✔ gotowy</source>
        <translation>✔ ready</translation>
    </message>
    <message>
        <location filename="../ui/render.py" line="139"/>
        <source>✔ zainstalowana</source>
        <translation>✔ installed</translation>
    </message>
    <message>
        <location filename="../ui/dock.py" line="741"/>
        <source>✖  Krok %d nie powiódł się: %s</source>
        <translation>✖  Step %d failed: %s</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source> – klucz API nie ma uprawnień do tej operacji albo modelu.</source>
        <translation> – the API key is not permitted to use this operation or model.</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source> – brak środków na koncie API. Doładuj konto u dostawcy (np. Claude Console › Settings › Billing); po wpłacie asystent zadziała bez zmian w ustawieniach.</source>
        <translation> – your API credit balance is too low. Top up the account with the provider (e.g. Claude Console › Settings › Billing); the assistant will work again without changing any settings.</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source>Wyszukiwanie w internecie jest niedostępne dla tego klucza API (administrator może je włączyć w Claude Console › Settings › Privacy) – asystent działa bez niego.</source>
        <translation>Web search is not available for this API key (an administrator can enable it in Claude Console › Settings › Privacy) – the assistant continues without it.</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source> – model „%s” jest niedostępny dla tego klucza. Wybierz inny model w ustawieniach wtyczki.</source>
        <translation> – model “%s” is not available for this key. Choose another model in the plugin settings.</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source> – opis projektu jest zbyt długi dla modelu. Usuń część warstw z projektu albo kliknij „Nowe polecenie”.</source>
        <translation> – the project description is too long for the model. Remove some layers from the project or click “New command”.</translation>
    </message>
    <message>
        <location filename="../llm_client.py"/>
        <source> – serwery dostawcy są chwilowo przeciążone, spróbuj ponownie za chwilę.</source>
        <translation> – the provider's servers are temporarily overloaded, please try again shortly.</translation>
    </message>
    <message>
        <location filename="../plan_model.py"/>
        <source>Nieznany typ usługi „%s” (dozwolone: WMS, WMTS, WFS, WCS).</source>
        <translation>Unknown service type “%s” (allowed: WMS, WMTS, WFS, WCS).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>liczba obiektów nieznana</source>
        <translation>feature count unknown</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>%d obiektów</source>
        <translation>%d features</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>%d obiekt</source>
        <translation>%d feature</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>%d obiekty</source>
        <translation>%d features</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>W pobranym archiwum ZIP nie ma danych przestrzennych, które QGIS potrafi otworzyć.</source>
        <translation>The downloaded ZIP archive contains no spatial data that QGIS can open.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrane dane OpenStreetMap nie zawierają obiektów do wczytania (sprawdź zapytanie Overpass: [out:xml] i „out body;&gt;;out skel qt;”).</source>
        <translation>The downloaded OpenStreetMap data contains no features to load (check the Overpass query: [out:xml] and “out body;&gt;;out skel qt;”).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Wynik „%s” jest pusty, choć warstwy wejściowe mają obiekty: %s.</source>
        <translation>Result “%s” is empty although the input layers have features: %s.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Obiekty nie mają poprawnych geometrii (puste albo nieskończone współrzędne) – dane mogły zostać uszkodzone, np. przez przeliczenie ze złego układu; użyj warstwy źródłowej.</source>
        <translation>The features have no valid geometries (empty or infinite coordinates) – the data may have been damaged, e.g. by reprojecting from a wrong CRS; use the source layer.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Współrzędne są nieskończone – dane zostały uszkodzone; użyj warstwy źródłowej.</source>
        <translation>The coordinates are infinite – the data has been damaged; use the source layer.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Zasięg „%s” w układzie warstwy (%s): x %.6g…%.6g, y %.6g…%.6g – liczby wyglądają na %s.</source>
        <translation>Extent of “%s” in the layer CRS (%s): x %.6g…%.6g, y %.6g…%.6g – the numbers look like %s.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Zasięgi warstw wejściowych w ogóle się nie pokrywają – leżą w innych miejscach mapy (inny obszar albo błędny układ współrzędnych).</source>
        <translation>The input layer extents do not overlap at all – they lie in different places on the map (a different area or a wrong coordinate reference system).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Dodano z usługi %s „%s”: %s</source>
        <translation>Added from %s service “%s”: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Przybliżono mapę do zasięgu usługi.</source>
        <translation>Zoomed the map to the service extent.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobieram dane: %s</source>
        <translation>Downloading data: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Sprawdzam adres: %s</source>
        <translation>Checking address: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrano „%s” (%s, %s)</source>
        <translation>Downloaded “%s” (%s, %s)</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrano „%s” (%s)</source>
        <translation>Downloaded “%s” (%s)</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Nie przypisuję układu %s warstwie „%s”: jej współrzędne (np. %.0f, %.0f) są w metrach, a ten układ jest w stopniach – obiekty trafiłyby poza kulę ziemską. Warstwa ma układ %s; jeśli leży w złym miejscu, sprawdź dane źródłowe zamiast zmieniać układ.</source>
        <translation>Not assigning CRS %s to layer “%s”: its coordinates (e.g. %.0f, %.0f) are in metres, but this CRS uses degrees – the features would end up off the globe. The layer has CRS %s; if it is in the wrong place, check the source data instead of changing the CRS.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Nie przypisuję układu %s warstwie „%s”: jej współrzędne (np. %.5f, %.5f) wyglądają na stopnie geograficzne, a ten układ jest w metrach. Właściwy układ to najpewniej EPSG:4326.</source>
        <translation>Not assigning CRS %s to layer “%s”: its coordinates (e.g. %.5f, %.5f) look like geographic degrees, but this CRS uses metres. The correct CRS is most likely EPSG:4326.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrane dane nie dają się otworzyć jako warstwa (%s).</source>
        <translation>The downloaded data cannot be opened as a layer (%s).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrany plik ZIP jest uszkodzony.</source>
        <translation>The downloaded ZIP file is corrupted.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Wynik kroku „%s” wymaga sprawdzenia: %s</source>
        <translation>The result of step “%s” needs checking: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Jeśli istniejąca warstwa projektu jest niepełna albo dotyczy innego obszaru, zamiast ją przekształcać pobierz nowe dane (np. z OpenStreetMap albo usług GUGiK). Sprawdź też warunek wyboru.</source>
        <translation>If the existing project layer is incomplete or covers a different area, download new data (e.g. from OpenStreetMap or GUGiK services) instead of transforming it. Also check the selection condition.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Sprawdź warunek wyboru albo to, czy obiekty rzeczywiście się nakładają.</source>
        <translation>Check the selection condition or whether the features actually overlap.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Dane są większe niż %d MB – ogranicz obszar albo zakres zapytania.</source>
        <translation>The data is larger than %d MB – narrow the area or the scope of the query.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>usługa %s w sieci wewnętrznej: %s</source>
        <translation>%s service on an internal network: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>QGIS nie wczytał warstwy „%s” z usługi %s. %s</source>
        <translation>QGIS could not load layer “%s” from the %s service. %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Overpass API przerwał zapytanie (zwykle limit czasu albo pamięci) – ogranicz obszar, np. do gminy.</source>
        <translation>Overpass API aborted the query (usually a time or memory limit) – narrow the area, e.g. to a single municipality.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Nie rozpoznano formatu pobranych danych (to może być strona WWW z komunikatem błędu zamiast danych).</source>
        <translation>The format of the downloaded data was not recognised (it may be a web page with an error message instead of data).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrane dane „%s” nie zawierają obiektów – zapytanie mogło objąć zły obszar albo zły warunek.</source>
        <translation>The downloaded data “%s” contains no features – the query may have covered the wrong area or used the wrong condition.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>brak układu</source>
        <translation>no CRS</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>stopnie (EPSG:4326)</source>
        <translation>degrees (EPSG:4326)</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>metry</source>
        <translation>metres</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>adres w sieci wewnętrznej: %s</source>
        <translation>address on an internal network: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwer zwrócił błąd %d.</source>
        <translation>The server returned error %d.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Usługa pod adresem %s nie odpowiada poprawnie jako %s: %s</source>
        <translation>The service at %s does not respond correctly as %s: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Usługa „%s” działa, ale nie ma warstwy pasującej do „%s”. Dostępne warstwy: %s.</source>
        <translation>Service “%s” works, but has no layer matching “%s”. Available layers: %s.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Warstwa „%s” usługi nie podaje obsługiwanego układu współrzędnych.</source>
        <translation>Service layer “%s” does not offer a supported coordinate reference system.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwer Overpass jest przeciążony – próbuję serwera zapasowego.</source>
        <translation>The Overpass server is overloaded – trying a backup server.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Ogranicz obszar zapytania (np. do gminy) albo spróbuj później.</source>
        <translation>Narrow the query area (e.g. to a single municipality) or try again later.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Nie udało się pobrać danych: %s</source>
        <translation>Could not download the data: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>nieznany</source>
        <translation>unknown</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Warstwa „%s” nie ma zasięgu.</source>
        <translation>Layer “%s” has no extent.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwer nie odpowiedział w wyznaczonym czasie – ogranicz obszar zapytania.</source>
        <translation>The server did not respond in time – narrow the query area.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Przekierowanie do sieci wewnętrznej zostało zablokowane.</source>
        <translation>A redirect to an internal network was blocked.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Warstwa „%s” nie ma siatki kafli (TileMatrixSet).</source>
        <translation>Layer “%s” has no tile matrix set (TileMatrixSet).</translation>
    </message>
    <message>
        <location filename="../services.py"/>
        <source>Adres usługi musi zaczynać się od http:// lub https://.</source>
        <translation>The service address must start with http:// or https://.</translation>
    </message>
    <message>
        <location filename="../services.py"/>
        <source>To nie wygląda na usługę WMTS (brak sekcji Contents).</source>
        <translation>This does not look like a WMTS service (no Contents section).</translation>
    </message>
    <message>
        <location filename="../services.py"/>
        <source>Usługa zgłosiła błąd: %s</source>
        <translation>The service reported an error: %s</translation>
    </message>
    <message>
        <location filename="../services.py"/>
        <source>Odpowiedź nie jest poprawnym dokumentem XML – sprawdź adres i typ usługi.</source>
        <translation>The response is not a valid XML document – check the address and service type.</translation>
    </message>
    <message>
        <location filename="../services.py"/>
        <source>Nie znaleziono warstw – czy to na pewno usługa %s?</source>
        <translation>No layers found – is this really a %s service?</translation>
    </message>
    <message>
        <location filename="../ui/render.py"/>
        <source>USŁUGA SIECIOWA</source>
        <translation>WEB SERVICE</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Pozwól AI wyszukiwać w internecie (adresy usług WMS/WFS, kody TERYT)</source>
        <translation>Allow AI to search the web (WMS/WFS service addresses, TERYT codes)</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Tylko Anthropic Claude. Wyszukiwanie wykonuje API Anthropic na podstawie Twojego polecenia – nie są wysyłane żadne dodatkowe dane projektu. Administrator organizacji musi je włączyć w Claude Console (Settings › Privacy); bez tego asystent działa bez wyszukiwania.</source>
        <translation>Anthropic Claude only. The search is run by the Anthropic API based on your command – no additional project data is sent. An organisation administrator must enable it in Claude Console (Settings › Privacy); otherwise the assistant works without search.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Kontynuuj mimo to</source>
        <translation>Continue anyway</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Wynik jest prawidłowy (np. w obszarze naprawdę nie ma obiektów) – wykonaj dalsze kroki</source>
        <translation>The result is correct (e.g. there really are no features in the area) – run the remaining steps</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Sprawdź wynik kroku i wybierz, co dalej.</source>
        <translation>Check the step result and choose what to do next.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Szukam przyczyny podejrzanego wyniku i poprawiam plan…</source>
        <translation>Looking for the cause of the suspicious result and correcting the plan…</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>⚠  Wynik kroku %d wymaga sprawdzenia: %s</source>
        <translation>⚠  The result of step %d needs checking: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Zakończ</source>
        <translation>Finish</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Wyszukiwanie w internecie: %s</source>
        <translation>Web search: %s</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Asystent może sam znaleźć przyczynę i poprawić plan. Jeśli taki wynik jest prawidłowy, kontynuuj.</source>
        <translation>The assistant can find the cause and correct the plan itself. If this result is correct, continue.</translation>
    </message>
    <message>
        <location filename="../ui/dock.py"/>
        <source>Szukam w internecie: %s</source>
        <translation>Searching the web: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwer Overpass %s nie odpowiedział poprawnie – ponawiam za chwilę na serwerze %s.</source>
        <translation>Overpass server %s did not respond correctly – retrying shortly on server %s.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwery Overpass API (OpenStreetMap) są teraz przeciążone – wtyczka przez ok. %d min ponawiała zapytanie na wszystkich serwerach zapasowych. To problem po stronie OpenStreetMap: kliknij „Ponów” za kilka minut.</source>
        <translation>Overpass API (OpenStreetMap) servers are overloaded right now – the plugin retried the query on all fallback servers for about %d min. This is a problem on the OpenStreetMap side: click “Retry” in a few minutes.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Wszystkie serwery Overpass są przeciążone – ponowię automatycznie za %d s (runda %d z %d). „Zatrzymaj” przerywa oczekiwanie.</source>
        <translation>All Overpass servers are overloaded – retrying automatically in %d s (round %d of %d). “Stop” cancels the wait.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwery OpenStreetMap przeciążone – ponowienie za %d s…</source>
        <translation>OpenStreetMap servers overloaded – retrying in %d s…</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Brak kodu TERYT powiatu dla paczki BDOT10k (np. „1418”; gmina „141805_2” też wystarczy – paczki są powiatowe).</source>
        <translation>Missing county TERYT code for the BDOT10k package (e.g. “1418”; a commune code such as “141805_2” also works – packages are per county).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Brak kodu klasy BDOT10k (np. OT_BUBD_A – budynki, OT_SKDR_L – drogi).</source>
        <translation>Missing BDOT10k class code (e.g. OT_BUBD_A – buildings, OT_SKDR_L – roads).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Klasa %s w paczce BDOT10k powiatu %s nie zawiera obiektów.</source>
        <translation>Class %s in the BDOT10k package of county %s contains no features.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Nie udało się pobrać paczki BDOT10k powiatu %s: %s</source>
        <translation>Could not download the BDOT10k package of county %s: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Paczka BDOT10k powiatu %s jest już pobrana – wczytuję klasę %s.</source>
        <translation>The BDOT10k package of county %s is already downloaded – loading class %s.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Paczka pod adresem %s jest niedostępna – próbuję kolejny format.</source>
        <translation>The package at %s is unavailable – trying the next format.</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobieram paczkę BDOT10k powiatu %s: %s</source>
        <translation>Downloading the BDOT10k package of county %s: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobieram: %s</source>
        <translation>Downloading: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobieram: %s z %s</source>
        <translation>Downloading: %s of %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrana paczka BDOT10k jest uszkodzona (ZIP).</source>
        <translation>The downloaded BDOT10k package is corrupted (ZIP).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Pobrano paczkę BDOT10k powiatu %s (%s).</source>
        <translation>Downloaded the BDOT10k package of county %s (%s).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Serwer GUGiK zwrócił coś innego niż archiwum ZIP (%s).</source>
        <translation>The GUGiK server returned something other than a ZIP archive (%s).</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>W paczce BDOT10k nie znaleziono klasy %s. Pliki w paczce: %s</source>
        <translation>Class %s was not found in the BDOT10k package. Files in the package: %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>Wczytano „%s” (%s) z BDOT10k powiatu %s</source>
        <translation>Loaded “%s” (%s) from BDOT10k of county %s</translation>
    </message>
    <message>
        <location filename="../executor.py"/>
        <source>brak paczki dla tego powiatu (sprawdź kod TERYT: %s).</source>
        <translation>no package for this county (check the TERYT code: %s).</translation>
    </message>
    <message>
        <location filename="../plan_model.py"/>
        <source>Brak kodu klasy BDOT10k (np. OT_BUBD_A).</source>
        <translation>Missing BDOT10k class code (e.g. OT_BUBD_A).</translation>
    </message>
    <message>
        <location filename="../ui/render.py"/>
        <source>powiat</source>
        <translation>county</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source> (warstwa id: %s)</source>
        <translation> (layer id: %s)</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Wykonano.</source>
        <translation>Done.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Serwer MCP nasłuchuje na %s</source>
        <translation>MCP server listening on %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Brak wyników.</source>
        <translation>No results.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Serwer MCP nie może nasłuchiwać na porcie %d: %s</source>
        <translation>The MCP server cannot listen on port %d: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Serwer MCP zatrzymany.</source>
        <translation>MCP server stopped.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Wywołanie narzędzia %s: %s</source>
        <translation>Tool call %s: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Krok wymagający działania użytkownika nie jest dostępny przez MCP.</source>
        <translation>Steps requiring user action are not available via MCP.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Kod PyQGIS nie jest dostępny przez MCP.</source>
        <translation>PyQGIS code is not available via MCP.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Adres w sieci wewnętrznej wymaga zgody: %s. Powtórz z allow_internal_network=true, jeśli użytkownik się zgadza.</source>
        <translation>An internal-network address requires consent: %s. Repeat with allow_internal_network=true if the user agrees.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>QGIS wykonuje jeszcze poprzednie polecenie – spróbuj ponownie za chwilę.</source>
        <translation>QGIS is still running the previous command – try again in a moment.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Nie znaleziono warstwy: %s</source>
        <translation>Layer not found: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Nie ma algorytmu: %s</source>
        <translation>No such algorithm: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Przekroczono limit czasu (%d min).</source>
        <translation>Time limit exceeded (%d min).</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Krok „%s” zakończył się błędem: %s</source>
        <translation>Step “%s” failed: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Wykonanie przerwane.</source>
        <translation>Execution aborted.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Ostrzeżenia:</source>
        <translation>Warnings:</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Dziennik:</source>
        <translation>Log:</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Akcje niedostępne przez MCP: %s</source>
        <translation>Actions not available via MCP: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Nieprawidłowe wywołanie: %s</source>
        <translation>Invalid call: %s</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Serwer MCP (Claude Desktop)</source>
        <translation>MCP server (Claude Desktop)</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Udostępnij QGIS aplikacji Claude Desktop (serwer MCP na tym komputerze)</source>
        <translation>Expose QGIS to the Claude Desktop app (MCP server on this computer)</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Nasłuchuje wyłącznie na 127.0.0.1 i wymaga tokenu. Claude Desktop łączy się przez most mcp_bridge.py z katalogu wtyczki. Kroki wymagające działania użytkownika ani kod PyQGIS nie są dostępne przez MCP; adresy w sieci wewnętrznej wymagają jawnej zgody w wywołaniu.</source>
        <translation>Listens on 127.0.0.1 only and requires a token. Claude Desktop connects through the mcp_bridge.py bridge from the plugin folder. Steps requiring user action and PyQGIS code are not available via MCP; internal-network addresses require explicit consent in the call.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Skopiuj konfigurację Claude Desktop</source>
        <translation>Copy Claude Desktop configuration</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Nowy token</source>
        <translation>New token</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Skopiowano do schowka fragment claude_desktop_config.json (zawiera token – nie udostępniaj go). Wklej go do pliku i uruchom Claude Desktop ponownie.</source>
        <translation>A claude_desktop_config.json snippet was copied to the clipboard (it contains the token – do not share it). Paste it into the file and restart Claude Desktop.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Wygenerowano nowy token – skopiuj konfigurację ponownie.</source>
        <translation>A new token was generated – copy the configuration again.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Port:</source>
        <translation>Port:</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Serwer MCP jest dostępny po ponownym uruchomieniu wtyczki.</source>
        <translation>The MCP server becomes available after the plugin is reloaded.</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Zatrzymany. Po zapisaniu z zaznaczoną opcją serwer uruchomi się od razu; następnie skopiuj konfigurację do Claude Desktop (Ustawienia › Developer › Edit Config).</source>
        <translation>Stopped. After saving with the option checked the server starts immediately; then copy the configuration into Claude Desktop (Settings › Developer › Edit Config).</translation>
    </message>
    <message>
        <location filename="../ui/settings_dialog.py"/>
        <source>Działa: %s. Po zmianie portu lub tokenu skopiuj konfigurację ponownie do claude_desktop_config.json i uruchom Claude Desktop od nowa.</source>
        <translation>Running: %s. After changing the port or token, copy the configuration into claude_desktop_config.json again and restart Claude Desktop.</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Warstwa „%s”: %s</source>
        <translation>Layer “%s”: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>krycie %d%%</source>
        <translation>opacity %d%%</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>widoczna</source>
        <translation>visible</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>ukryta</source>
        <translation>hidden</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>na wierzchu</source>
        <translation>on top</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>na spodzie</source>
        <translation>at the bottom</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>bez zmian</source>
        <translation>no changes</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Pominięto (symbolizacja inna niż pojedynczy symbol albo niepasujący typ geometrii): %s</source>
        <translation>Skipped (renderer other than single symbol, or geometry type does not match): %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>kolor %s</source>
        <translation>colour %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>Nieprawidłowy kolor: %s</source>
        <translation>Invalid colour: %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>obrys %s</source>
        <translation>stroke %s</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>szerokość obrysu %.2f mm</source>
        <translation>stroke width %.2f mm</translation>
    </message>
    <message>
        <location filename="../mcp_server.py"/>
        <source>rozmiar %.2f mm</source>
        <translation>size %.2f mm</translation>
    </message>
</context>
</TS>
