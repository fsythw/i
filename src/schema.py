
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
    data_type: str
    is_primary_key: bool
    description: str
    

class Metadata(BaseModel):
    table_name: str
    description: str
    columns: List[Column]
    relationships: List[Relationship]

class MetadataNoRel(BaseModel):
    table_name: str
    description: str
    columns: List[Column]

class Data(BaseModel):
    database_name: str
    database_desc: str
    metadata: List[Metadata]