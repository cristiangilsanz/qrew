from com.qode.qrew.v1.service.core.search import (
    SearchConfig,
    SearchField,
    Weight,
    create_trigger_sql,
    drop_trigger_sql,
    normalise_query,
    update_all_sql,
    update_one_sql,
    vector_sql,
)


def _events_config() -> SearchConfig:
    return SearchConfig(
        name="events",
        table="events",
        fields=[
            SearchField("name", Weight.A),
            SearchField("description", Weight.B),
        ],
    )


def test_normalise_query_collapses_whitespace() -> None:
    assert normalise_query("  hello   world  ") == "hello world"


def test_normalise_query_empty_input_yields_empty_string() -> None:
    assert normalise_query("   ") == ""


def test_vector_sql_concatenates_weighted_to_tsvector_terms() -> None:
    sql = vector_sql(_events_config())
    assert "to_tsvector('simple'" in sql
    assert "'A'" in sql
    assert "'B'" in sql
    assert "||" in sql


def test_update_all_sql_updates_every_row() -> None:
    sql = update_all_sql(_events_config())
    assert sql.startswith("UPDATE events SET search_vector =")


def test_update_one_sql_binds_row_id() -> None:
    sql = update_one_sql(_events_config())
    assert "WHERE id = :row_id" in sql


def test_create_trigger_sql_references_new_columns() -> None:
    sql = create_trigger_sql(_events_config())
    assert "NEW.name" in sql
    assert "NEW.description" in sql
    assert "events_search_vector_trigger" in sql


def test_drop_trigger_sql_drops_function_and_trigger() -> None:
    sql = drop_trigger_sql(_events_config())
    assert "DROP TRIGGER IF EXISTS" in sql
    assert "DROP FUNCTION IF EXISTS" in sql
