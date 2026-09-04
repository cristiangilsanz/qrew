# builds the sql fragments that implement a full text search query
from dataclasses import dataclass

from pagination import decode_cursor, encode_cursor
from com.qode.qrew.v1.catalog.repositories.events.search.config import SearchConfig
from com.qode.qrew.v1.catalog.repositories.events.search.tsvector import (
    escape_like,
    normalise_query,
    to_prefix_tsquery,
)


@dataclass(frozen=True)
class SearchClause:
    rank_expression: str | None
    where_fragments: list[str]
    parameters: dict[str, object]
    order_by: str


# builds the where clause rank expression and cursor for a search request
def build_search_clause(
    *,
    config: SearchConfig,
    q: str | None,
    filters: dict[str, object] | None = None,
    cursor: str | None = None,
) -> SearchClause:
    parameters: dict[str, object] = {}
    where: list[str] = []
    rank_expression: str | None = None
    order_by = f"{config.primary_key} DESC"

    if q is not None and normalise_query(q):
        cleaned = normalise_query(q)
        # the query has to appear as a contiguous run of characters, since a prefix
        # tsquery matches its words apart from one another and drops the ones the
        # language treats as stopwords, which let a two word query return the whole
        # catalogue. this filter stands on its own, so a query made only of
        # punctuation narrows the results instead of widening them.
        parameters["ilike_q"] = f"%{escape_like(cleaned)}%"
        name_col = next(
            (f.column_name for f in config.fields if f.weight == "A"),
            config.fields[0].column_name if config.fields else "name",
        )
        desc_col = next(
            (f.column_name for f in config.fields if f.weight == "B"),
            None,
        )
        ilike_clauses = [f"{name_col} ILIKE :ilike_q ESCAPE '\\'"]
        if desc_col:
            ilike_clauses.append(f"coalesce({desc_col}, '') ILIKE :ilike_q ESCAPE '\\'")
        where.append(f"({' OR '.join(ilike_clauses)})")

        # the vector only orders what the filter returned, so a query it cannot
        # express leaves the ranking out rather than the results
        prefix_q = to_prefix_tsquery(cleaned)
        if prefix_q:
            parameters["search_q"] = prefix_q
            tsquery = f"to_tsquery('{config.language}', :search_q)"
            rank_expression = f"ts_rank_cd({config.vector_column}, {tsquery})"
            order_by = f"{config.rank_column_alias} DESC, {config.primary_key} DESC"

    for column, value in (filters or {}).items():
        if value is None:
            continue
        param_name = f"filter_{column}"
        parameters[param_name] = value
        where.append(f"{column} = :{param_name}")

    if cursor is not None and rank_expression is not None:
        rank_value, last_id = decode_cursor(cursor)
        parameters["cursor_rank"] = rank_value
        parameters["cursor_id"] = last_id
        where.append(
            f"({rank_expression} < :cursor_rank OR "
            f"({rank_expression} = :cursor_rank "
            f"AND {config.primary_key} < :cursor_id))"
        )

    return SearchClause(
        rank_expression=rank_expression,
        where_fragments=where,
        parameters=parameters,
        order_by=order_by,
    )


# encodes the pagination cursor for the next page of results
def encode_next_cursor(last_rank: float, last_id: str) -> str:
    return encode_cursor(last_rank, last_id)
