import enum
from dataclasses import dataclass, field


class Weight(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class SearchField:
    column_name: str
    weight: Weight = Weight.D


@dataclass(frozen=True)
class SearchConfig:
    """Declarative description of a tsvector-backed search target."""

    name: str
    table: str
    fields: list[SearchField]
    language: str = "simple"
    vector_column: str = "search_vector"
    primary_key: str = "id"
    rank_column_alias: str = "search_rank"

    @property
    def trigger_name(self) -> str:
        return f"{self.table}_search_vector_trigger"

    @property
    def trigger_function_name(self) -> str:
        return f"{self.table}_search_vector_update"

    @property
    def index_name(self) -> str:
        return f"ix_{self.table}_search_vector"

    def field_columns(self) -> list[str]:
        return [field_.column_name for field_ in self.fields]

    def weights_in_definition_order(self) -> list[Weight]:
        return [field_.weight for field_ in self.fields]


def merge_fields(*fields: SearchField) -> list[SearchField]:
    """Convenience for use in test fixtures."""
    return list(fields)


__all__ = ["SearchConfig", "SearchField", "Weight", "field", "merge_fields"]
