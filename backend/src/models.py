from pydantic import BaseModel, model_validator


class HexCoord(BaseModel):
    col: int
    row: int


class PoiSummary(BaseModel):
    id: str
    name: str
    col: int
    row: int
    color: str
    visible: bool = True


class PoiDetail(PoiSummary):
    description: str
    notes: str
    path: list[HexCoord] | None = None


class PoiWrite(BaseModel):
    name: str
    color: str
    description: str
    notes: str
    visible: bool = True
    col: int | None = None
    row: int | None = None
    path: list[HexCoord] | None = None

    @model_validator(mode="after")
    def validate_position(self) -> "PoiWrite":
        has_static_position = self.col is not None and self.row is not None
        has_path = self.path is not None

        if has_path and len(self.path) == 0:
            raise ValueError("path must contain at least one coordinate")

        if has_static_position == has_path:
            raise ValueError("provide either col/row or path")

        if (self.col is None) != (self.row is None):
            raise ValueError("col and row must be provided together")

        return self


class PoiCreate(PoiWrite):
    id: str


class PoiUpdate(PoiWrite):
    pass


class PoiPatch(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None
    notes: str | None = None
    visible: bool | None = None
    col: int | None = None
    row: int | None = None
    path: list[HexCoord] | None = None

    @model_validator(mode="after")
    def validate_position(self) -> "PoiPatch":
        has_static = self.col is not None or self.row is not None
        has_path = self.path is not None

        if has_static and has_path:
            raise ValueError("provide either col/row or path, not both")

        if (self.col is None) != (self.row is None):
            raise ValueError("col and row must be provided together")

        if has_path and len(self.path) == 0:
            raise ValueError("path must contain at least one coordinate")

        return self
