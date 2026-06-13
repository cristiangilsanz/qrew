from dataclasses import dataclass

from com.qode.qrew.v1.catalog.core.api.page import decode_cursor, encode_cursor
from com.qode.qrew.v1.catalog.core.search.config import SearchConfig
from com.qode.qrew.v1.catalog.core.search.tsvector import normalise_query


@dataclass(frozen=True)
class SearchClause:
    rank_expression: str | None
    where_fragments: list[str]
    parameters: dict[str, object]
    order_by: str


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
        parameters["search_q"] = cleaned
        tsquery = f"websearch_to_tsquery('{config.language}', :search_q)"
        where.append(f"{config.vector_column} @@ {tsquery}")
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


def encode_next_cursor(last_rank: float, last_id: str) -> str:
    return encode_cursor(last_rank, last_id)
