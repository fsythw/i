import itertools
import polars as pl
from datetime import datetime
import re 
import os
import json
from src.embeddings import get_similar_tables


def discover_primary_key(df: pl.DataFrame) -> list[str]:

    n_rows = df.height
    columns = df.columns
    candidates = []

    # Check all 1- and 2-column combinations
    for r in [1, 2]:
        for combo in itertools.combinations(columns, r):
            if df.select(combo).null_count().sum_horizontal().max() > 0:
                continue  # skip if any nulls
            if df.select(combo).unique().height == n_rows:
                candidates.append(combo)

    # float, datetime
    def is_likely_key(cols):
        for col in cols:
            dtype = df[col].dtype
            if dtype in [pl.Float64, pl.Float32] or "Datetime" in str(dtype):
                return False
        return True

    filtered = [c for c in candidates if is_likely_key(c)]
    if not filtered:
        return []

    # prefer single-column keys first
    single = [c for c in filtered if len(c) == 1]
    if single:
        return list(single[0])

    return list(filtered[0])  # fallback to first composite


def find_valid_foreign_keys_from_csv(target_table, all_tables, csv_dir, embed_fn, top_n=10):
    confirmed_fk = []
    print("before similar tables")
    similar_tables = get_similar_tables(target_table, all_tables, top_n)
    print(similar_tables)

    # Load target table dataframe
    fk_df_path = os.path.join(csv_dir, f"{target_table['table_name']}.csv")
    if not os.path.exists(fk_df_path):
        return []

    fk_df = pl.read_csv(fk_df_path, rechunk=False, try_parse_dates=True, ignore_errors=True)

    for fk_col in target_table["columns"]:
        fk_col_name = fk_col["name"]
        fk_col_type = fk_col["data_type"]


        for candidate_table in similar_tables:
            pk_df_path = os.path.join(csv_dir, f"{candidate_table['table_name']}.csv")
            if not os.path.exists(pk_df_path):
                continue

            pk_df = pl.read_csv(pk_df_path,rechunk=False, try_parse_dates=True, ignore_errors=True)

            for pk_col in candidate_table["columns"]:
                

                if pk_col["data_type"] != fk_col_type:
                    continue

                pk_col_name = pk_col["name"]
                print(pk_col_name, fk_col_name)


                #check inclusion 
                unmatched = fk_df.join(pk_df, left_on=fk_col_name, right_on=pk_col_name, how="anti")
                if unmatched.is_empty():
                    confirmed_fk.append({
                        "from_table": target_table["table_name"],
                        "from_column": fk_col_name,
                        "to_table": candidate_table["table_name"],
                        "to_column": pk_col_name,
                        "match_type": "value_inclusion"
                    })
    print(confirmed_fk, sep="\n")
    return confirmed_fk



    
def save_relationships(enriched_metadata: list[dict], data_dir: str = "data"):
    for table in enriched_metadata:
        table_name = table["table_name"]
        file_path = os.path.join(data_dir, f"{table_name}.json")
        
        if not os.path.exists(file_path):
            print(f"Metadata file for {table_name} not found. Skipping.")
            continue
        
        with open(file_path, "r") as f:
            metadata = json.load(f)

        metadata["relationships"] = table.get("relationships", [])

        with open(file_path, "w") as f:
            json.dump(metadata, f, indent=2)
