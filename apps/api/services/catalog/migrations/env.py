import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from com.qode.qrew.v1.catalog.core.database import Base
from com.qode.qrew.v1.catalog import models  # noqa: F401 — register all models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(
    object: object,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    if type_ == "table":
        schema = getattr(object, "schema", None)
        return schema == "catalog"
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,  # type: ignore[arg-type]
        version_table="alembic_version_catalog",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,  # type: ignore[arg-type]
        version_table="alembic_version_catalog",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    db_url = os.environ.get(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url") or "",
    )
    connectable = create_async_engine(db_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
