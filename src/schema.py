
from pydantic import BaseModel
from typing import List


class Relationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    reason: str

class Column(BaseModel):
    name: str
    type: str
    description: str
    example_value: List[str]

class Metadata(BaseModel):
    table_name: str
    description: str
    tags: List[str]
    columns: List[Column]
    relationships: List[Relationship] = []

class MetadataNoRel(BaseModel):
    table_name: str
    description: str
    tags: List[str]
    columns: List[Column]

class Data(BaseModel):
    database_name: str
    metadata: List[Metadata]