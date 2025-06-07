import streamlit as st
import pandas as pd
import json

from src.models import Metadata, MetadataNoRel, Data
from src.prompts import generate_prompt
from src.llm import call_llm_2, enrich_metadata_with_relationships

st.title("CSV Metadata Explorer")

N_SAMPLE_ROWS = 5

uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_metadata = []

    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split('.')[0]
        df = pd.read_csv(uploaded_file)
        st.subheader(f"{table_name}")


        sample_data = (
            df.drop_duplicates()
            .sample(n=N_SAMPLE_ROWS, random_state=42)
            .to_dict(orient="records")
        )
        st.dataframe(sample_data)
        columns = list(df.columns)

        prompt = generate_prompt(table_name, sample_data, columns)
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



    if st.button("Enrich with Relationships"):
        enrichment_prompt = json.dumps([m.model_dump() for m in all_metadata], indent=2)
        enriched_response = enrich_metadata_with_relationships(all_metadata)

        try:
            data_obj = Data.model_validate_json(enriched_response)
            st.subheader("Enriched Metadata")
            st.json(data_obj.model_dump())
        except Exception as e:
            st.error(f"Enrichment failed: {e}")
