from sqlalchemy.dialects.sqlite import dialect

from api.app.utils.sql import build_where_clause


def test_build_where_clause_expressions():
    expr = build_where_clause({"phone": "123", "bad": "1=1"})
    compiled = expr.compile(dialect=dialect())
    sql = str(compiled)
    assert "phone" in sql
    assert "bad" not in sql
    assert "123" in compiled.params.values()
