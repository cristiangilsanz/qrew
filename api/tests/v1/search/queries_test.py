from com.qode.qrew.v1.service.core.search import (
    SearchConfig,
    SearchField,
    Weight,
    build_search_clause,
    encode_next_cursor,
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


def test_empty_query_produces_filter_only_clause() -> None:
    clause = build_search_clause(
        config=_events_config(), q=None, filters={"category": "concerts"}
    )
    assert clause.rank_expression is None
    assert "category = :filter_category" in clause.where_fragments
    assert clause.parameters["filter_category"] == "concerts"


def test_text_query_adds_rank_and_match() -> None:
    clause = build_search_clause(config=_events_config(), q="hello world")
    assert clause.rank_expression is not None
    assert any("websearch_to_tsquery" in f for f in clause.where_fragments)
    assert clause.parameters["search_q"] == "hello world"
    assert "search_rank" in clause.order_by


def test_filters_skip_none_values() -> None:
    clause = build_search_clause(
        config=_events_config(),
        q=None,
        filters={"category": None, "venue_city": "Madrid"},
    )
    assert any("venue_city = :filter_venue_city" in f for f in clause.where_fragments)
    assert "filter_category" not in clause.parameters


def test_cursor_only_applied_alongside_a_text_query() -> None:
    raw_cursor = encode_next_cursor(0.5, "event-id-42")
    without_q = build_search_clause(config=_events_config(), q=None, cursor=raw_cursor)
    assert "cursor_rank" not in without_q.parameters
    with_q = build_search_clause(config=_events_config(), q="qrew", cursor=raw_cursor)
    assert with_q.parameters["cursor_id"] == "event-id-42"
    assert "cursor_rank" in with_q.parameters
