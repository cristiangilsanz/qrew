# covers how a search query turns into the clause that filters the catalogue
from com.qode.qrew.v1.catalog.repositories.events.search.config import (
    SearchConfig,
    SearchField,
    Weight,
)
from com.qode.qrew.v1.catalog.repositories.events.search.queries import build_search_clause
from com.qode.qrew.v1.catalog.repositories.events.search.tsvector import escape_like

_CONFIG = SearchConfig(
    name="events",
    table="catalog.events",
    primary_key="id",
    vector_column="search_vector",
    language="spanish",
    fields=[
        SearchField(column_name="name", weight=Weight.A),
        SearchField(column_name="description", weight=Weight.B),
    ],
)


class TestEscapeLike:
    # verifies that a wildcard the visitor types matches itself
    def test_it_neutralises_the_wildcards(self) -> None:
        assert escape_like("100%") == "100\\%"
        assert escape_like("a_b") == "a\\_b"
        assert escape_like("back\\slash") == "back\\\\slash"

    # verifies that ordinary text passes through untouched
    def test_it_leaves_plain_text_alone(self) -> None:
        assert escape_like("Event A") == "Event A"


class TestBuildSearchClause:
    # verifies that the query has to appear as one contiguous run
    def test_it_filters_by_a_contiguous_match(self) -> None:
        clause = build_search_clause(config=_CONFIG, q="Event A")
        where = " ".join(clause.where_fragments)
        assert "ILIKE :ilike_q" in where
        assert clause.parameters["ilike_q"] == "%Event A%"

    # verifies that the loose prefix query no longer decides what comes back,
    # since it dropped stopwords and matched words apart from one another
    def test_it_does_not_filter_by_the_prefix_query(self) -> None:
        clause = build_search_clause(config=_CONFIG, q="Event A")
        assert "@@" not in " ".join(clause.where_fragments)

    # verifies that the vector still orders what the match returns
    def test_it_still_ranks_by_relevance(self) -> None:
        clause = build_search_clause(config=_CONFIG, q="Event A")
        assert clause.rank_expression is not None
        assert "ts_rank_cd" in clause.rank_expression

    # verifies that a wildcard cannot widen the match to the whole catalogue
    def test_a_typed_wildcard_does_not_match_everything(self) -> None:
        clause = build_search_clause(config=_CONFIG, q="%")
        assert clause.parameters["ilike_q"] == "%\\%%"

    # verifies that an empty query filters nothing
    def test_an_empty_query_adds_no_clause(self) -> None:
        assert build_search_clause(config=_CONFIG, q="   ").where_fragments == []

    # verifies that a query the vector cannot express still narrows the results
    def test_a_query_of_punctuation_still_filters(self) -> None:
        clause = build_search_clause(config=_CONFIG, q="%")
        assert "ILIKE :ilike_q" in " ".join(clause.where_fragments)
        assert clause.rank_expression is None
