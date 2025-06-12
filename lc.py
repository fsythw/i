## pip install langchain_google_genai
import streamlit ##.env


import polars as pl
import json
import time
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Configuration ---

lc = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=streamlit.secrets['google']["GENAI_API_KEY"])

# one-shot example
ONE_SHOT_EXAMPLE = {
    "name": "GENDER",
    "data_type": "string",
    "is_primary_key": False,
    "example_values": ["M", "F"],
    "description": "Patient's gender, recorded as either 'M' (male) or 'F' (female)."
}

# --- Step 1: Extract data types and primary key candidates using Polars ---
df = pl.read_csv("C:\\Users\\admin\\Downloads\\3\\ABCD1234.csv", rechunk=False, try_parse_dates=True)
dtypes = df.dtypes
print(df.dtypes)
unique_counts = df.select(pl.all().n_unique()).row(0)
null_counts = df.null_count().row(0)
n_rows = df.height

schema_info = []
for col, dtype, uniq, nulls in zip(df.columns, dtypes, unique_counts, null_counts):
    schema_info.append({
        "name": col,
        "data_type": str(dtype),
        "is_primary_key": (uniq == n_rows and nulls == 0),
        "example_values": df[col].unique().sample(n=3, seed=42).to_list(),
    })
# print(json.dumps(schema_info, indent=2, default=str))

# --- Step 2: Call Gemini to generate descriptions, excluding dtype/PK ---clear
def call_gemini_descriptions(columns):
    prompt = f"""
You are a clinical data assistant. Your job is to write meaningful, specific descriptions for dataset columns.

You will be given:
- column name
- some example values

Avoid vague phrases. Use the context of values to help explain what each column likely represents.

Here is an example:
{json.dumps(ONE_SHOT_EXAMPLE, indent=2)}

Here is your data:
{json.dumps(columns, indent=2, default=str)}
"""
    response = lc.invoke(
        prompt, generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.content)



llm_input = [{"name": col["name"], "example_values": col["example_values"]} for col in schema_info]
llm_output = call_gemini_descriptions(llm_input)
# print(json.dumps(llm_output, indent=2))

# Merge back
for col in schema_info:
    match = next((item for item in llm_output if item["name"] == col["name"]), {})
    col["description"] = match.get("description", "No description provided.")
print(json.dumps(schema_info, indent=2, default=str))


def call_gemini_table_description(table_name, schema_info):
    prompt = f"""
You are a clinical data assistant. Your job is to write a concise and informative description for a dataset table based on its name and column information.

Table Name: "{table_name}"

Column Information:
{json.dumps(schema_info, indent=2)}

Based on the table name and the descriptions of the columns, write a brief overview of the table's content and purpose.
"""
    response = lc.invoke(prompt)
    return response.content

table_description = call_gemini_table_description("ADMISSIONS", schema_info)
print(f"Table Description for ADMISSIONS:\n{table_description}")


final_metadata = { ## GENERALISE THIS
    "table_name": "ADMISSIONS",
    "description": table_description,
    "columns": schema_info
}

print(json.dumps(final_metadata, indent=2))


# --- Step 3: Refine descriptions using LangChain memory ---
memory = ConversationBufferMemory(return_messages=True)
conversation = ConversationChain(
    llm=lc,
    memory=memory,
    verbose=False,
)

refined_schema = []
for col in schema_info:
    context = {
        "target_column": col,
        "other_columns": [c for c in schema_info if c["name"] != col["name"]]
    }


improvement_prompt = f"""
You are refining metadata descriptions. Improve the target column's description using other column names and values as context.

Only return the new description.

Input:
{json.dumps(context, indent=2)}
"""
improved = conversation.predict(input=improvement_prompt).strip()
col["description"] = improved
refined_schema.append(col)
time.sleep(1)


# --- Step 4: LLM-as-a-Critic Evaluation ---
def evaluate_descriptions(schema):
    critic_prompt = f"""
You are a data quality reviewer. Score each column description on a scale of 0–10 based on clarity, precision, and usefulness.

Only return feedback for any item scoring below 7.

Input:
{json.dumps(schema, indent=2)}
"""
    response = lc.invoke(
        critic_prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.content)

critic_scores = evaluate_descriptions(refined_schema)
time.sleep(1)

# --- Step 5: Auto-improve based on Critic Feedback ---
# for critique in critic_scores:
#     if critique.get("score", 0) < 7 and "feedback" in critique:
#         target = next(col for col in refined_schema if col["name"] == critique["name"])
#         improvement = conversation.predict(input=f"""
# Original: {target['description']}

# Feedback: {critique['feedback']}

# Please rewrite the description to address the issues.
# """).strip()
#         target["description"] = improvement
#         time.sleep(1)

# --- Step 6: Output JSON ---
with open("final_metadata.json", "w") as f:
    json.dump(refined_schema, f, indent=2)

print("✅ Final enriched metadata written to final_metadata.json")
