from com.qode.qrew.v1.identity.core.search.config import SearchConfig


def normalise_query(raw: str) -> str:
    """Clean a user-supplied query string before handing it to Postgres."""
    return " ".join(raw.split()).strip()


def vector_sql(config: SearchConfig) -> str:
    """Return the SQL expression that builds a row's search vector."""
    parts: list[str] = []
    for field in config.fields:
        parts.append(
            f"setweight(to_tsvector('{config.language}', "
            f"coalesce({field.column_name}, '')), '{field.weight}')"
        )
    return " || ".join(parts)


def update_all_sql(config: SearchConfig) -> str:
    """Return the SQL to recompute the search vector for every row."""
    body = vector_sql(config)
    return f"UPDATE {config.table} SET {config.vector_column} = {body}"


def update_one_sql(config: SearchConfig) -> str:
    """Return the parameterised SQL to recompute a single row's vector."""
    body = vector_sql(config)
    return (
        f"UPDATE {config.table} SET {config.vector_column} = {body} "
        f"WHERE {config.primary_key} = :row_id"
    )


def create_trigger_sql(config: SearchConfig) -> list[str]:
    """Return the statements that install a trigger to keep the vector up to date."""
    body = vector_sql(config).replace("coalesce(", "coalesce(NEW.")
    return [
        f"CREATE OR REPLACE FUNCTION {config.trigger_function_name}() "
        "RETURNS trigger AS $$ BEGIN "
        f"NEW.{config.vector_column} := {body}; "
        "RETURN NEW; "
        "END; $$ LANGUAGE plpgsql",
        f"DROP TRIGGER IF EXISTS {config.trigger_name} ON {config.table}",
        f"CREATE TRIGGER {config.trigger_name} BEFORE INSERT OR UPDATE "
        f"ON {config.table} FOR EACH ROW "
        f"EXECUTE FUNCTION {config.trigger_function_name}()",
    ]


def drop_trigger_sql(config: SearchConfig) -> list[str]:
    """Return the statements that remove the trigger and its function."""
    return [
        f"DROP TRIGGER IF EXISTS {config.trigger_name} ON {config.table}",
        f"DROP FUNCTION IF EXISTS {config.trigger_function_name}()",
    ]
