import json, pathlib
SCHEMA = json.loads(pathlib.Path("schemas/survey.schema.json").read_text())
def test_schema_lists_all_types():
    types = SCHEMA["definitions"]["question"]["properties"]["type"]["enum"]
    assert set(types) == {"single_choice","multi_choice","dropdown","yes_no","short_text","long_text","number",
        "rating","nps","likert","matrix","ranking","slider","date","email","phone","file","statement","consent","group"}
def test_minimal_survey_keys():
    assert SCHEMA["required"] == ["title", "questions"]
