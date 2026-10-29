# -*- coding: utf-8 -*-
import pytest

from gis_assistant_ai import utils


class TestExtractJson:
    def test_plain(self):
        assert utils.extract_json('{"type": "answer", "text": "ok"}')["type"] == "answer"

    def test_code_fence_and_prose(self):
        text = 'Oto plan:\n```json\n{"type": "plan", "steps": []}\n```\nPowodzenia!'
        assert utils.extract_json(text)["type"] == "plan"

    def test_braces_inside_strings(self):
        obj = utils.extract_json('prefix {"text": "a } b { c", "n": 1} suffix')
        assert obj == {"text": "a } b { c", "n": 1}

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            utils.extract_json("   ")

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            utils.extract_json("to nie jest JSON")


class TestSanitizeSource:
    def test_password_and_user(self):
        src = "dbname='gis' host=10.0.0.5 user='jan' password='Tajne123' sslmode=disable"
        out = utils.sanitize_source(src, "postgres")
        assert "Tajne123" not in out and "jan" not in out

    def test_userinfo_in_url(self):
        out = utils.sanitize_source("url=https://jan:haslo@example.com/wms?token=abc123&layers=x", "wms")
        assert "haslo" not in out and "abc123" not in out and "layers=x" in out

    def test_authcfg(self):
        assert "a1b2c3d" not in utils.sanitize_source("url=https://x.pl/wfs authcfg=a1b2c3d", "WFS")

    def test_local_path_shortened(self):
        out = utils.sanitize_source("C:/Users/jan/Projekty/tajny/dzialki.gpkg|layername=dzialki", "ogr")
        assert "Users" not in out and out.startswith("dzialki.gpkg")


def test_redact_key():
    assert utils.redact_key("Błąd: klucz sk-ant-XYZ odrzucony", "sk-ant-XYZ") == "Błąd: klucz *** odrzucony"
    assert utils.redact_key("bez klucza", "") == "bez klucza"


class TestRefs:
    lookup = staticmethod(lambda sid, key: {"s1": {"OUTPUT": "layer_1"}}[sid][key or "OUTPUT"])

    def test_whole_value(self):
        assert utils.resolve_refs("{{s1}}", self.lookup) == "layer_1"

    def test_nested_and_inline(self):
        out = utils.resolve_refs({"INPUT": "{{ s1.OUTPUT }}", "X": ["id={{s1}}"]}, self.lookup)
        assert out == {"INPUT": "layer_1", "X": ["id=layer_1"]}

    def test_find_refs(self):
        assert utils.find_refs({"a": "{{s1}}", "b": ["{{s2.OUTPUT}}", 5]}) == {"s1", "s2"}


class TestSafety:
    @pytest.mark.parametrize("url", ["https://plugins.qgis.org/plugins/x/", "http://example.com/a?b=1"])
    def test_web_urls_allowed(self, url):
        assert utils.is_web_url(url)

    @pytest.mark.parametrize("url", ["file:///C:/Windows/system32/calc.exe", "ms-settings:", "smb://srv/share",
                                     "javascript:alert(1)", "", None, "https:// spacja"])
    def test_other_schemes_blocked(self, url):
        assert not utils.is_web_url(url)

    def test_python_risks(self):
        code = "import os\nos.system('dir')\nopen('x.txt','w').write('a')\nimport requests"
        risks = utils.python_risks(code)
        assert "system operacyjny (os)" in risks and "odczyt/zapis plików (open)" in risks
        assert "połączenia sieciowe" in risks

    def test_python_safe_code(self):
        code = "layer = get_layer(results['s1']['OUTPUT'])\nlayer.setOpacity(0.5)\nlayer.triggerRepaint()"
        assert utils.python_risks(code) == []


def test_plugin_slug():
    assert utils.plugin_slug_from_url("https://plugins.qgis.org/plugins/uldk_gugik/") == "uldk_gugik"
