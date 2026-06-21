from com.qode.qrew.v1.catalog.repositories.events.search.config import SearchConfig


def normalise_query(raw: str) -> str:
    return " ".join(raw.split()).strip()


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
