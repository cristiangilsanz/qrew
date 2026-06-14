from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_database(database_url: str, *, echo: bool = False):
    """Creates a database engine and session factory from a connection URL."""
    engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return engine, session_factory, get_db
