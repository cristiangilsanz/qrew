from com.qode.qrew.v1.catalog.repositories.events.search.config import SearchConfig


import re as _re


def normalise_query(raw: str) -> str:
    return " ".join(raw.split()).strip()


def to_prefix_tsquery(raw: str) -> str:
    """Convert a raw search string to a prefix-matching tsquery value.

    Each word becomes 'word:*' so 'par eve' matches 'party event'.
    Non-alphanumeric characters are stripped to avoid tsquery syntax errors.
    """
    words = [_re.sub(r"[^\w]", "", w) for w in raw.split()]
    words = [w for w in words if w]
    if not words:
        return ""
    return " & ".join(f"{w}:*" for w in words)


def vector_sql(config: SearchConfig) -> str:
    parts: list[str] = []
    for field in config.fields:
        parts.append(
            f"setweight(to_tsvector('{config.language}', "
            f"coalesce({field.column_name}, '')), '{field.weight}')"
        )
    return " || ".join(parts)


def update_all_sql(config: SearchConfig) -> str:
    body = vector_sql(config)
    return f"UPDATE {config.table} SET {config.vector_column} = {body}"


def update_one_sql(config: SearchConfig) -> str:
    body = vector_sql(config)
    return (
        f"UPDATE {config.table} SET {config.vector_column} = {body} "
        f"WHERE {config.primary_key} = :row_id"
    )
