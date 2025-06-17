import streamlit as st
import polars as pl
import json

from google import genai

from src.models import Data
from src.prompts import call_gemini_descriptions, call_gemini_table_description, judge_and_improve_table_schema, enrich_metadata_with_relationships

client = genai.Client(api_key=st.secrets['google']["GENAI_API_KEY"])
ONE_SHOT_EXAMPLE = {
    "name": "GENDER",
    "data_type": "string",
    "is_primary_key": False,
    "example_values": ["M", "F"],
    "description": "Patient's gender, recorded as either 'M' (male) or 'F' (female)."
}

st.title("CSV Metadata Explorer")



uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_metadata = []

    for uploaded_file in uploaded_files:
        table_name = uploaded_file.name.split('.')[0]
        df = pl.read_csv(uploaded_file, rechunk=False, try_parse_dates=True, ignore_errors=True)
        st.subheader(f"{table_name}")

        # sample_data = (
        #     df.drop_duplicates()
        #     .sample(n=N_SAMPLE_ROWS, random_state=42)
        #     .to_dict(orient="records")
        # )
        # st.dataframe(sample_data)

        unique_counts = df.select(pl.all().n_unique()).row(0)
        null_counts = df.null_count().row(0)
        n_rows = df.height

        schema_info = []
        for col, dtype, uniq, nulls in zip(df.columns, df.dtypes, unique_counts, null_counts):
            schema_info.append({
                "name": col,
                "data_type": str(dtype),
                "is_primary_key": (uniq == n_rows and nulls == 0),
                "example_values": df[col].unique().sample(n=3, seed=42, with_replacement=True).to_list(),
            })

        
        llm_input = [{"name": col["name"], "example_values": col["example_values"]} for col in schema_info]
        llm_output = call_gemini_descriptions(llm_input, ONE_SHOT_EXAMPLE, client)
        print(llm_output) # returns list

        for col in schema_info:
            match = next((item for item in llm_output if item["name"] == col["name"]), {})
            col["description"] = match.get("description", "No description provided.")
            col.pop("example_values", None)
        print(json.dumps(schema_info, indent=2, default=str))

        table_description = call_gemini_table_description(table_name, schema_info, client)
        print(f"Table Description for {table_name}:\n{table_description}", table_name)


        # memory = ConversationBufferMemory(return_messages=True)
        # conversation = ConversationChain(
        #     llm=lc,
        #     memory=memory,
        #     verbose=False,
        # )

        MAX_ITERATIONS = 3
        SCORE_THRESHOLD = 8
        refined_schema = []
        print("\n")
        print("LOOPING")
        refined_schema = judge_and_improve_table_schema(table_name, schema_info, client)
        print(refined_schema)

        final_metadata = { ## GENERALISE THIS
            "table_name": table_name,
            "description": table_description,
            "columns": refined_schema
        }

        print(json.dumps(final_metadata, indent=2, default=str))
        
        # column_metadata = [
        #     {
        #         "name": col["name"],
        #         "data_type": col["data_type"],
        #         "is_primary_key": col["is_primary_key"],
        #         "description": col["description"]
        #     }
        #     for col in refined_schema
        # ]

        st.write(table_description)
        st.subheader("column metadata)")
        st.dataframe(refined_schema, use_container_width=True)

        st.subheader("json")
        st.json(final_metadata)



        # try:
        #   metadata_no_rel_obj = MetadataNoRel.model_validate_json(final_metadata)
        #   metadata_obj = Metadata(**metadata_no_rel_obj.model_dump())
        all_metadata.append(final_metadata)


        # except Exception as e:
        #   st.error(f"Failed to parse metadata: {e}")

        # print("\n")
        # print("ALL METADATA")
        # print(all_metadata)
    # Optional enrichment (Pass 2)
    # if st.button("Enrich with Relationships"):
    #     enrichment_prompt = json.dumps([m.model_dump() for m in all_metadata], indent=2)
    #     enriched_response = enrich_metadata_with_relationships(all_metadata)

    #     try:
    #         data_obj = Data.model_validate_json(enriched_response)
    #         st.subheader("Enriched Metadata")
    #         st.json(data_obj.model_dump())
    #     except Exception as e:
    #         st.error(f"Enrichment failed: {e}")

    if st.button("Enrich with Relationships"):
        enriched_response = enrich_metadata_with_relationships(all_metadata, client)

        try:
            data_obj = Data.model_validate_json(json.dumps(enriched_response))
            st.subheader("Enriched Metadata")
            st.json(data_obj.model_dump())
        except Exception as e:
            st.error(f"Enrichment failed: {e}")