import json, time
from src.schema import Data


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


def judge_and_improve_table_schema(table_name, schema_info, client, threshold=8, max_iter=1):
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

def enrich_metadata_with_relationships(metadata_list, fk_list, client):
    prompt = f"""
    You are an expert in relational databases. Given a list of metadata of other tables and potential foreign keys, evaluate which foreign key relationships are valid.

    Criteria:
    - The column in the source table must reference the primary key of the destination table.
    - Consider column names, data types, and descriptions.
    Return the enriched metadata for all the tables.

    Schemas:
    {json.dumps(metadata_list, indent=2)}

    Foreign key list:{fk_list}

    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"response_mime_type": "application/json",
                "response_schema": Data}

    )

    try:
        return json.loads(response.text)
    except Exception as e:
        print("Failed to parse enriched response:", e)
        return metadata_list  # fallback to original
