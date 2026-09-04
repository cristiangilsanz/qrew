# builds the sql that maintains a table's search vector column
from com.qode.qrew.v1.catalog.repositories.events.search.config import SearchConfig


import re as _re


# collapses a raw search query to single spaced words
def normalise_query(raw: str) -> str:
    return " ".join(raw.split()).strip()


# neutralises the wildcards a like pattern would otherwise read as operators
def escape_like(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# turns a normalised query into a prefix matching tsquery expression
def to_prefix_tsquery(raw: str) -> str:
    words = [_re.sub(r"[^\w]", "", w) for w in raw.split()]
    words = [w for w in words if w]
    if not words:
        return ""
    return " & ".join(f"{w}:*" for w in words)


# builds the expression that combines a row's weighted fields into a vector
def vector_sql(config: SearchConfig) -> str:
    parts: list[str] = []
    for field in config.fields:
        parts.append(
            f"setweight(to_tsvector('{config.language}', "
            f"coalesce({field.column_name}, '')), '{field.weight}')"
        )
    return " || ".join(parts)


# builds the statement that refreshes every row's search vector
def update_all_sql(config: SearchConfig) -> str:
    body = vector_sql(config)
    return f"UPDATE {config.table} SET {config.vector_column} = {body}"


# builds the statement that refreshes one row's search vector
def update_one_sql(config: SearchConfig) -> str:
    body = vector_sql(config)
    return (
        f"UPDATE {config.table} SET {config.vector_column} = {body} "
        f"WHERE {config.primary_key} = :row_id"
    )
