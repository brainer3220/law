from __future__ import annotations

import json


def test_map_case_obj_to_row_basic():
    from law_shared.scripts.pg_load_jsonl import map_case_obj_to_row

    obj = {
        "id": 123,
        "casetype": "민사",
        "casename": "근로시간 면제 관련 판결",
        "facts": "원고는 근로시간면제 한도를 초과...",
    }
    row = map_case_obj_to_row(obj, source="train.jsonl", lineno=10)
    # (doc_id, title, body, meta_json, path)
    assert row[0] == "123"
    assert row[1] == obj["casename"]
    assert row[2] == obj["facts"]
    meta = json.loads(row[3])
    assert meta["casetype"] == "민사"
    assert row[4] == "train.jsonl:10"


def test_map_case_obj_to_row_missing_id_uses_fallback():
    from law_shared.scripts.pg_load_jsonl import map_case_obj_to_row

    obj = {"casename": "X", "facts": "Y"}
    row = map_case_obj_to_row(obj, source="x.jsonl", lineno=1)
    assert row[0] == "x.jsonl:1"
    assert row[1] == "X"
    assert row[2] == "Y"
