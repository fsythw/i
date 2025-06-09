import json
from src.models import Metadata

def generate_prompt(table_name, sample_data, columns, table_description=""):
    return f"""
You are a data catalog assistant. Your task is to generate metadata for a dataset.

Table name: "{table_name}"
{f"Table description: {table_description}" if table_description else ""}

Sample data:
{json.dumps(sample_data, indent=2)}

Columns:
{columns}

For each column, provide:
- name
- type (e.g., string, integer, float, date, boolean)
- description. If it might be a primary or foreign key, indicate so.
- Example values from the sample
Use the table-level description provided. 

Output the metadata as a JSON object.
"""

def generate_enrichment_prompt(metadata_list: list[Metadata]) -> str:
    metadata_jsons = [m.model_dump() for m in metadata_list]
    return f"""
You are a metadata enrichment assistant. Your task is to analyze multiple tables' metadata and enrich each with possible relationships to other tables.

Here is the current metadata for all tables:
{json.dumps(metadata_jsons, indent=2)}

Instructions:
- For each table, look at all columns and try to identify if any of them reference another table's primary key.
- Add a "relationships" key to each table, with a list of relationship objects.


Return the full metadata for the database.
"""