import streamlit as st
import polars as pl
import json
import os

from google import genai
from src.prompts import (
    call_gemini_descriptions,
    call_gemini_table_description,
    judge_and_improve_table_schema,
    enrich_metadata_with_relationships,
)
from src.visualisation import convert_to_er_graphviz
from src.utils import discover_primary_key, find_valid_foreign_keys_from_csv
from src.cache import compute_file_hash, is_cached, add_to_cache
from src.embeddings import get_embedding

client = genai.Client(api_key=st.secrets["google"]["GENAI_API_KEY"])
DATA_DIR = "data"
CSV_DIR = "csv_data"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

ONE_SHOT_EXAMPLE = {
    "name": "GENDER",
    "data_type": "string",
    "is_primary_key": False,
    "example_values": ["M", "F"],
    "statistic": [{"statistic": "count", "GENDER": "46520"}, {"statistic": "null_count", "GENDER": "0"}],
    "description": "Patient's gender, recorded as either 'M' (male) or 'F' (female)."
}

# Load metadata cache
def load_all_metadata():
    try:
        with open("all_metadata.json", "r") as f:
            return {table["table_name"]: table for table in json.load(f)}
    except FileNotFoundError:
        return {}

cached_metadata = load_all_metadata()

# === Helper: Generate metadata for one table ===
def generate_metadata_from_csv(file, table_name):
    file_hash = compute_file_hash(file)
    metadata_file_path = os.path.join(DATA_DIR, f"{table_name}.json")

    # Save CSV
    csv_path = os.path.join(CSV_DIR, f"{table_name}.csv")
    with open(csv_path, "wb") as f:
        f.write(file.getbuffer())

    add_to_cache(file_hash, file.name, metadata_file_path)

    df = pl.read_csv(csv_path, rechunk=False, try_parse_dates=True, ignore_errors=True)
    pk_cols = set(discover_primary_key(df))
    n_rows = df.height
    unique_counts = df.select(pl.all().n_unique()).row(0)
    null_counts = df.null_count().row(0)

    schema_info = []
    for col, dtype, uniq, nulls in zip(df.columns, df.dtypes, unique_counts, null_counts):
        stats = df.select(col).drop_nulls().describe().to_dicts()
        schema_info.append({
            "name": col,
            "data_type": str(dtype),
            "is_primary_key": col in pk_cols,
            "n_unique": uniq,
            "example_values": df[col].unique().sample(n=3, seed=42, with_replacement=True).to_list(),
            "statistics": stats,
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

    # Save to disk
    with open(metadata_file_path, "w") as f:
        json.dump(final_metadata, f, indent=2)

    return final_metadata

# === Streamlit UI ===
st.title("📊 CSV Metadata Explorer")

uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split('.')[0]
        
        file_hash = compute_file_hash(uploaded_file)

        if is_cached(file_hash):
            st.info(f"✅ {table_name} already processed.")
            
        else:
            st.success(f"Processing new file: {table_name}")
            new_meta = generate_metadata_from_csv(uploaded_file, table_name)
            cached_metadata[table_name] = new_meta
        with open(f"data/{table_name}.json", 'r') as file:
                df = json.load(file)
        st.header(table_name)
        st.write(df["description"])
        st.subheader("Column Metadata")
        st.dataframe(df["columns"], use_container_width=True)
        
        st.download_button(
            label="Download JSON",
            file_name=f"{table_name}.json",
            mime="application/json",
            data=json.dumps(df),
            key=f"download_{table_name}"
        )
        continue

    with open("all_metadata.json", "w") as f:
        json.dump(list(cached_metadata.values()), f, indent=2)

    st.success("All uploaded files have been processed and metadata saved.")

# === Relationship Discovery ===
st.header("🔗 Discover Table Relationships")

specific_file = st.file_uploader("Upload a single CSV to find its relationships", type="csv")

if specific_file:
    table_name = specific_file.name.split('.')[0]

    # Ensure metadata is available
    if table_name not in cached_metadata:
        st.warning(f"No metadata found for {table_name}, generating it now...")
        meta = generate_metadata_from_csv(specific_file, table_name)
        cached_metadata[table_name] = meta

        with open("all_metadata.json", "w") as f:
            json.dump(list(cached_metadata.values()), f, indent=2)

    target_metadata = cached_metadata[table_name]

    if st.button("Find Relationships"):
        st.info("Finding foreign key relationships...")
        fk_matches = find_valid_foreign_keys_from_csv(
            target_table=target_metadata,
            all_tables=list(cached_metadata.values()),
            csv_dir=CSV_DIR,
            embed_fn=get_embedding,
            top_n=10
        )
        st.subheader("🔍 Foreign Key Candidates")
        st.json(fk_matches)

        enriched = enrich_metadata_with_relationships(list(cached_metadata.values()), fk_matches, client)

        try:
            enriched_metadata = enriched["metadata"]
            db_desc = enriched.get("database_name", "Untitled Database")
            st.subheader("📘 Enriched Metadata")
            st.write(f"**Database Description:** {db_desc}")
            st.json(enriched_metadata)

            with open("all_metadata.json", "w") as f:
                json.dump(enriched_metadata, f, indent=2)

            st.subheader("🗺️ ER Diagram")
            # diagram = convert_to_er_graphviz(enriched_metadata)
            # st.graphviz_chart(diagram)
            focus_table = st.selectbox("visualisations", options=[t["table_name"] for t in cached_metadata.values()])
            #depth = st.slider("degree of rls", min_value=1, max_value=3, value=2)

            dot = convert_to_er_graphviz(list(cached_metadata.values()), focus_table=focus_table, degree=1)
            st.graphviz_chart(dot)
            dot = convert_to_er_graphviz(list(cached_metadata.values()), focus_table=focus_table, degree=2)
            st.graphviz_chart(dot)
            dot = convert_to_er_graphviz(list(cached_metadata.values()), focus_table=focus_table, degree=3)
            st.graphviz_chart(dot)

        except Exception as e:
            st.error(f"Failed to parse enriched metadata: {e}")
