from pydantic import BaseModel, Field, JsonValue, field_validator


class Column(BaseModel):
    """A discovered source column; type is a source-defined type name."""

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    nullable: bool = True

    model_config = {"extra": "forbid"}


class DiscoveredTable(BaseModel):
    """Source metadata and an optional, explicitly fetched preview."""

    name: str = Field(min_length=1)
    # Alias avoids colliding with Pydantic's legacy BaseModel.schema() method.
    schema_: list[Column] = Field(alias="schema")
    preview: list[dict[str, JsonValue]] | None = Field(default=None, max_length=100)

    model_config = {"extra": "forbid"}

    @property
    def schema(self) -> list[Column]:
        return self.schema_

    @field_validator("schema_")
    @classmethod
    def unique_columns(cls, columns):
        names = [column.name for column in columns]
        if len(names) != len(set(names)):
            raise ValueError("Discovered schema must contain unique column names.")
        return columns
