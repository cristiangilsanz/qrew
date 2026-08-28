# declares the full text search configuration shared by every searchable table
import enum
from dataclasses import dataclass


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
    name: str
    table: str
    fields: list[SearchField]
    language: str = "simple"
    vector_column: str = "search_vector"
    primary_key: str = "id"
    rank_column_alias: str = "search_rank"

    # names the trigger that keeps the search vector current
    @property
    def trigger_name(self) -> str:
        return f"{self.table}_search_vector_trigger"

    # names the function the trigger calls
    @property
    def trigger_function_name(self) -> str:
        return f"{self.table}_search_vector_update"

    # names the index over the search vector
    @property
    def index_name(self) -> str:
        return f"ix_{self.table}_search_vector"

    # lists the columns that feed the search vector
    def field_columns(self) -> list[str]:
        return [field_.column_name for field_ in self.fields]

    # lists the weight of every field in declaration order
    def weights_in_definition_order(self) -> list[Weight]:
        return [field_.weight for field_ in self.fields]


__all__ = ["SearchConfig", "SearchField", "Weight"]
