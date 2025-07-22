import streamlit as st
import polars as pl
import json
import os
from google import genai
from bson.json_util import dumps
from src.visualisation import convert_to_er_graphviz
from src.mongo import get_mongo_client
from src.embeddings import get_embedding
from src.prompts import enrich_metadata_with_relationships
from src.utils import find_valid_foreign_keys_from_csv, save_relationships

st.title("2. explore")

def load_all_metadata():
    try:
        with open("all_metadata.json", "r") as f:
            return {table["table_name"]: table for table in json.load(f)}
    except FileNotFoundError:
        return {}

cached_metadata = load_all_metadata()

DATA_DIR = "data"
CSV_DIR = "csv_data"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

# Connect to MongoDB
mongo_client = get_mongo_client()
db = mongo_client["metadata"]

collection_names = db.list_collection_names()

selected_table = st.selectbox("Select a table", collection_names)

if selected_table:
    collection = db[selected_table]
    doc = collection.find_one({}, {'_id':False})

    
    if doc:
        st.header(f"{doc['table_name']}")
        st.markdown(f"**Description:** {doc['description']}")
        
        # Column metadata
        st.subheader("Column Metadata")
        col_df = pl.DataFrame(doc["columns"])
        st.dataframe(col_df, use_container_width=True)

        if st.button("Find Relationships"):
            st.info("Finding foreign key relationships...")
            fk_matches = find_valid_foreign_keys_from_csv(
                target_table=doc,
                all_tables=list(cached_metadata.values()),
                csv_dir=CSV_DIR,
                embed_fn=get_embedding,
                top_n=8
            )
  
   
            enriched = enrich_metadata_with_relationships(list(cached_metadata.values()), fk_matches, genai.Client(api_key=os.environ.get("GENAI_API_KEY")))

            print(enriched["metadata"])
            save_relationships(enriched["metadata"])
            try:
            

                dot = convert_to_er_graphviz(enriched["metadata"])
                print(dot)
                st.graphviz_chart(dot)
                #st.json(enriched["metadata"])
                    

            except Exception as e:
                st.error(f"Failed to parse enriched metadata: {e}")

    else:
        st.warning("Table metadata not found.")





    