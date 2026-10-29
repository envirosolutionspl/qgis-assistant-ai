# -*- coding: utf-8 -*-
import json

from gis_assistant_ai import plan_model


def _plan(steps):
    return json.dumps({"type": "plan", "title": "T", "steps": steps})


def test_parse_plan_normalizes_actions_and_ids():
    resp = plan_model.parse_response(_plan([
        {"id": "s1", "action": "uldk", "title": "Granica", "teryt": "1418"},
        {"id": "s1", "action": "run_algorithm", "algorithm": "native:buffer", "params": {"DISTANCE": 100}},
        {"action": "zoom_to_layer", "layer": "{{s1}}"},
    ]))
    actions = [s["action"] for s in resp["steps"]]
    ids = [s["id"] for s in resp["steps"]]
    assert actions == ["uldk_boundary", "processing", "zoom"]
    assert len(set(ids)) == 3
    assert all(s["_status"] == "pending" for s in resp["steps"])


def test_unknown_action_becomes_note_with_warning():
    resp = plan_model.parse_response(_plan([{"action": "teleport", "title": "?"}]))
    step = resp["steps"][0]
    assert step["action"] == "note" and step["_warnings"]


def test_model_cannot_set_private_fields():
    resp = plan_model.parse_response(_plan([{"action": "note", "title": "x", "_status": "done",
                                             "_error": "hack"}]))
    step = resp["steps"][0]
    assert step["_status"] == "pending" and "_error" not in step


def test_executable_returns_bool():
    assert plan_model.executable(None) is False
    assert plan_model.executable({"type": "answer"}) is False
    assert plan_model.executable({"type": "plan", "steps": [{"action": "note"}]}) is False
    assert plan_model.executable({"type": "plan", "steps": [{"action": "zoom"}]}) is True


def test_best_match_within_provider():
    ids = ["quickosm:downloadosmdatainareaquery", "quickosm:downloadosmdataaroundareaquery",
           "quickosm:downloadosmdataextentquery", "quickosm:buildqueryinsidearea"]
    assert plan_model.best_match("quickosm:downloadosmdatabyarea", ids) == "quickosm:downloadosmdatainareaquery"
    assert plan_model.best_match("quickosm:cosnieistniejacego", ids) is None
    assert plan_model.best_match("quickosm:x", []) is None


def test_add_service_normalized():
    steps = plan_model.normalize_steps([
        {"action": "add_wms", "url": " https://sdi.gdos.gov.pl/wms ", "layer": "Parki narodowe"},
        {"action": "add_service", "service_type": "SHP", "url": "https://x.pl"},
    ])
    assert steps[0]["action"] == "add_service" and steps[0]["service_type"] == "wms"
    assert steps[0]["url"] == "https://sdi.gdos.gov.pl/wms" and steps[0]["layers"] == ["Parki narodowe"]
    assert steps[1]["_warnings"]


def test_bdot10k_step_normalization():
    out = plan_model.normalize({"type": "plan", "steps": [
        {"action": "bdot10k", "layer": "OT_SKDR_L", "powiat": ["1418"], "name": "Drogi"},
        {"action": "bdot10k_layer", "teryt": "1418"}]})
    s1, s2 = out["steps"]
    assert s1["action"] == "bdot10k_layer" and s1["class"] == "OT_SKDR_L" and s1["teryt"] == "1418"
    assert s2["action"] == "bdot10k_layer" and s2["class"] == "" and s2["_warnings"]


def test_alg_aliases_fix_select_by_location():
    assert plan_model.ALG_ALIASES["qgis:selectbylocation"] == "native:selectbylocation"
    assert all(k != v for k, v in plan_model.ALG_ALIASES.items())     # alias na samego siebie nic nie poprawia


def test_service_types_shared_with_services():
    from gis_assistant_ai import services
    assert plan_model.SERVICE_TYPES is services.TYPES
