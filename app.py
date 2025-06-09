import streamlit as st
import pandas as pd
import json
import os

from src.models import Metadata, MetadataNoRel, Data
from src.prompts import generate_prompt
from src.llm import call_llm_2, enrich_metadata_with_relationships

st.title("CSV Metadata Explorer")

N_SAMPLE_ROWS = 20


description_path = os.path.join("data", "desc.json")
try:
    with open(description_path, "r") as f:
        table_descriptions = json.load(f)
except Exception as e:
    st.warning(f"Could not load table descriptions: {e}")
    table_descriptions = {}


uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_metadata = []

    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split('.')[0]
        df = pd.read_csv(uploaded_file)
        st.subheader(f"{table_name}")

        default_description = table_descriptions.get(table_name, "")
        table_description = st.text_area(f"Description for `{table_name}`", default_description)

        st.markdown(table_description)

        sample_data = (
            df.drop_duplicates()
            .sample(n=N_SAMPLE_ROWS, random_state=42)
            .to_dict(orient="records")
        )
        st.dataframe(sample_data)
        columns = list(df.columns)

        prompt = generate_prompt(table_name, sample_data, columns, table_description)
        llm_response = call_llm_2(prompt)

        try:
          metadata_no_rel_obj = MetadataNoRel.model_validate_json(llm_response)
          metadata_obj = Metadata(**metadata_no_rel_obj.model_dump())
          all_metadata.append(metadata_obj)

          st.markdown(f"### Description for `{table_name}`")
          st.write(metadata_obj.description)

          columns_df = pd.DataFrame([col.model_dump() for col in metadata_obj.columns])
          columns_df = columns_df[["name", "type", "description", "example_value"]]

          st.markdown("### Column Metadata")
          st.dataframe(columns_df, use_container_width=True)

          with st.expander("Show Raw JSON"):
            st.json(metadata_obj.model_dump())

          st.markdown("### Export")
          metadata_json = json.dumps(metadata_obj.model_dump(), indent=2)
          st.download_button("Download JSON", metadata_json, file_name=f"{table_name}_metadata.json", mime="application/json")

        except Exception as e:
          st.error(f"Failed to parse metadata: {e}")
