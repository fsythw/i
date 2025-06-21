import streamlit as st
import polars as pl
import json

from google import genai
from src.prompts import call_gemini_descriptions, call_gemini_table_description, judge_and_improve_table_schema, enrich_metadata_with_relationships
from src.visualisation import render_er_diagram

client = genai.Client(api_key=st.secrets['google']["GENAI_API_KEY"])
ONE_SHOT_EXAMPLE = {
    "name": "GENDER",
    "data_type": "string",
    "is_primary_key": False,
    "example_values": ["M", "F"],
    "description": "Patient's gender, recorded as either 'M' (male) or 'F' (female).",
    "statistic": [{'statistic': 'count', 'GENDER': '46520'}, {'statistic': 'null_count', 'GENDER': '0'}, {'statistic': 'mean', 'GENDER': None}, {'statistic': 'std', 'GENDER': None}, {'statistic': 'min', 'GENDER': 'F'}, {'statistic': '25%', 'GENDER': None}, {'statistic': '50%', 'GENDER': None}, {'statistic': '75%', 'GENDER': None}, {'statistic': 'max', 'GENDER': 'M'}]
}

# def get_representative_values(series, max_len=20):
#     unique_vals = series.unique()
#     if len(unique_vals) <= max_len:
#         return unique_vals.to_list()
#     # Otherwise, sample intelligently
#     return series.sample(n=min(max_len, len(series)), seed=42, with_replacement=False).to_list()
# Load existing metadata if it exists
try:
    with open("all_metadata.json", "r") as f:
        cached_data = json.load(f)
except FileNotFoundError:
    cached_data = []

# Turn into a dictionary keyed by table name
cached_metadata = {table["table_name"]: table for table in cached_data}


st.title("CSV Metadata Explorer")



uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    new_metadata = []

    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split('.')[0]

        # 🛑 Skip if already cached
        if table_name in cached_metadata:
            st.info(f"✅ Skipped {table_name} (already processed)")
            continue

        df = pl.read_csv(uploaded_file, rechunk=False, try_parse_dates=True, ignore_errors=True)
        st.subheader(f"{table_name}")

        unique_counts = df.select(pl.all().n_unique()).row(0)
        null_counts = df.null_count().row(0)
        n_rows = df.height

        schema_info = []
        for col, dtype, uniq, nulls in zip(df.columns, df.dtypes, unique_counts, null_counts):
            stats = df.select(col).drop_nulls().describe().to_dicts()
            schema_info.append({
                "name": col,
                "data_type": str(dtype),
                "is_primary_key": (uniq == n_rows and nulls == 0),
                "example_values": df[col].unique().sample(n=3, seed=42, with_replacement=True).to_list(),
                "statistics": stats
            })

        llm_input = [{"name": col["name"], "example_values": col["example_values"], "statistics": col["statistics"]} for col in schema_info]
        llm_output = call_gemini_descriptions(llm_input, ONE_SHOT_EXAMPLE, client)

        for col in schema_info:
            match = next((item for item in llm_output if item["name"] == col["name"]), {})
            col["description"] = match.get("description", "No description provided.")
            col.pop("example_values", None)
            col.pop("statistics", None)

        table_description = call_gemini_table_description(table_name, schema_info, client)

        refined_schema = judge_and_improve_table_schema(table_name, schema_info, client)

        final_metadata = {
            "table_name": table_name,
            "description": table_description,
            "columns": refined_schema
        }

        st.write(table_description)
        st.subheader("📄 Column Metadata")
        st.dataframe(refined_schema, use_container_width=True)
        st.subheader("📦 Final Metadata (JSON)")
        st.json(final_metadata)

        new_metadata.append(final_metadata)

    # Merge new into cached
    for table in new_metadata:
        cached_metadata[table["table_name"]] = table

    # Write updated cache
    with open("all_metadata.json", "w") as f:
        json.dump(list(cached_metadata.values()), f, indent=2)

    st.success("✅ Metadata updated and saved.")




    # if st.button("Enrich with Relationships"):
    #     enriched_response = enrich_metadata_with_relationships(all_metadata, client)

    #     try:
    #         all_metadata = enriched_response["metadata"]
    #         db_desc = enriched_response.get("database_name", "Untitled")
    #         st.subheader("w/ relationships")
    #         st.write(f"database description: {db_desc}")
    #         st.json(all_metadata)
    #         with open("all_metadata.json", "w") as f:
    #             json.dump(all_metadata, f, indent=2)

    #     except Exception as e:
    #         st.error(f"Enrichment failed: {e}")
    if st.button("Enrich with Relationships"):
        enriched_response = enrich_metadata_with_relationships(list(cached_metadata.values()), client)

        try:
            enriched_metadata = enriched_response["metadata"]
            db_desc = enriched_response.get("database_name", "Untitled")
            st.subheader("📡 Enriched Metadata")
            st.write(f"📚 Database description: {db_desc}")
            st.json(enriched_metadata)

            with open("all_metadata.json", "w") as f:
                json.dump(enriched_metadata, f, indent=2)
            
            st.subheader("📊 ER Diagram")
            diagram = render_er_diagram(enriched_metadata)
            st.graphviz_chart(diagram)

        except Exception as e:
            st.error(f"Enrichment failed: {e}")
