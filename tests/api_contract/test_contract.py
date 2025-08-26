from schemathesis.openapi import from_path
from pathlib import Path

SCHEMA = from_path(Path(__file__).resolve().parents[2] / "openapi.json")


def test_openapi_contract() -> None:
    """Ensure critical endpoints exist in the schema."""
    assert list(SCHEMA.include(path_regex="^/orders").get_all_operations())
    assert list(SCHEMA.include(path_regex="bill").get_all_operations())
    assert list(SCHEMA.include(path_regex="exports").get_all_operations())
