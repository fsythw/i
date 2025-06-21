import json, time
from src.models import Metadata, Data

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
- Add a "relationships" key to each table, with a list of relationship objects. A relationship should appear in both tables.


Return the full metadata for the database.
"""


def call_gemini_descriptions(columns, example, client):
    prompt = f"""
You are a clinical data assistant. Your job is to write meaningful, specific descriptions for dataset columns.

You will be given:
- column name
- some example values
- summary statistics of the column

Avoid vague phrases. Use the context of values to help explain what each column likely represents.

Here is an example:
{json.dumps(example, indent=2)}

Here is your data:
{json.dumps(columns, indent=2, default=str)}
"""
    result = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt,
        config={
          "response_mime_type": "application/json",
        },
    )


    response_raw = result.text 
    response = json.loads(response_raw)
    return response



def call_gemini_table_description(table_name, schema_info, client):
    prompt = f"""
You are a clinical data assistant. Your job is to write a concise and informative description for a dataset table based on its name and column information.

Table Name: "{table_name}"

Column Information:
{json.dumps(schema_info, indent=2, default=str)}

Based on the table name and the descriptions of the columns, write a brief overview of the table's content and purpose.
"""
    response = client.models.generate_content(
      model="gemini-2.0-flash",
      contents=prompt
      
    )
    return response.text


def judge_and_improve_table_schema(table_name, schema_info, client, threshold=8, max_iter=3):
    current_schema = schema_info

    for iteration in range(max_iter):
        prompt = f"""
        You are a data documentation expert.

        Given the metadata for a table named `{table_name}`, evaluate the overall quality of column descriptions. Consider:
        - clarity, precision
        - how well the descriptions reflect inter-column relationships
        - whether the descriptions make sense together as a coherent schema
        - if a column is not a primary key, make sure the description is unambiguous and does not mention "unique" or any similar variation.

        Respond in **strict JSON** format:
        {{
          "score": <int from 1 to 10>,
          "comments": "<short feedback>",
          "suggested_improvements": [
            {{
              "name": "COLUMN_NAME",
              "new_description": "Improved version of the column description using table context"
            }},
            ...
          ]
        }}

        Current schema:
        {json.dumps(current_schema, indent=2, default=str)}
        """

        result = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config={
            "response_mime_type": "application/json",
            },
        )


        response_raw = result.text 
    

        try:
            response = json.loads(response_raw)
        except Exception:
            return current_schema  # fallback to last good schema

        score = response.get("score", 0)
        print(score)
        if score >= threshold:
            break  # done refining

        # Apply suggested improvements
        improvements = {item["name"]: item["new_description"] for item in response.get("suggested_improvements", [])}
        for col in current_schema:
            if col["name"] in improvements:
                col["description"] = improvements[col["name"]]

        time.sleep(1)

    return current_schema


def enrich_metadata_with_relationships(metadata_list, client):
    prompt = f"""
    Given the following table schemas, identify potential foreign key relationships between tables. 
    Use data type, column description, and primary key status to infer if a column references another table's primary key.
    Also give a description of the entire database.
    


    Schemas:
    {json.dumps(metadata_list, indent=2)}
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"response_mime_type": "application/json",
                "response_schema": Data,}

    )

    try:
        return json.loads(response.text)
    except Exception as e:
        print("Failed to parse enriched response:", e)
        return metadata_list  # fallback to original
