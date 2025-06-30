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

# def find_inclusion_dependencies_from_metadata(metadata, error_threshold=0.1):
#     fk_candidates = []

#     pk_index = {
#         (table["table_name"], col["name"]): col
#         for table in metadata
#         for col in table["columns"]
#         if col.get("is_primary_key")
#     }

#     for table in metadata:
#         for col in table["columns"]:
#             if col.get("is_primary_key"):
#                 continue
#             fk_min, fk_max = col.get("min"), col.get("max")
#             fk_name = col["name"]
#             fk_table = table["table_name"]

#             for (pk_table, pk_col), pk_meta in pk_index.items():
#                 pk_min, pk_max = pk_meta.get("min"), pk_meta.get("max")

#                 # If any min/max missing, skip
#                 if None in [fk_min, fk_max, pk_min, pk_max]:
#                     continue

#                 if fk_min >= pk_min and fk_max <= pk_max:
#                     fk_candidates.append({
#                         "from_table": fk_table,
#                         "from_column": fk_name,
#                         "to_table": pk_table,
#                         "to_column": pk_col,
#                         "match_type": "range_inclusion"
#                     })

#     return fk_candidates

# import polars as pl
# import os

# def find_inclusion_dependencies_from_metadata(metadata, error_threshold=0.0):
#     fk_candidates = []

#     pk_index = {
#         (table["table_name"], col["name"]): [col["unique_values_path"], col["data_type"]]
#         for table in metadata
#         for col in table["columns"]
#         if col.get("is_primary_key") and os.path.exists(col.get("unique_values_path", ""))
#     }
#     print(pk_index)

#     for table in metadata:
#         for col in table["columns"]:
#             if col.get("is_primary_key"):
#                 continue

#             fk_table = table["table_name"]
#             fk_col = col["name"]
#             fk_path = col.get("unique_values_path", "")
#             print(fk_path)
#             fk_type = col.get("data_type")
#             print(fk_type)
            
#             if not os.path.exists(fk_path):
#                 continue

#             fk_vals = pl.read_parquet(fk_path).select(fk_col).unique()

#             for (pk_table, pk_col), (pk_path, pk_type) in pk_index.items():
#                 if pk_type != fk_type:
#                     continue

#                 pk_vals = pl.read_parquet(pk_path).select(pk_col).unique()

#                 unmatched = pk_vals.join(fk_vals, on=pk_col, how="anti").to_dicts()

#                 if not unmatched:
#                     fk_candidates.append({
#                         "from_table": fk_table,
#                         "from_column": fk_col,
#                         "to_table": pk_table,
#                         "to_column": pk_col,
#                         "match_type": "value_inclusion",

#                     })

#     return fk_candidates



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

        # Skip primary keys as foreign keys
        # if fk_col.get("is_primary_key"):
        #     continue

        for candidate_table in similar_tables:
            pk_df_path = os.path.join(csv_dir, f"{candidate_table['table_name']}.csv")
            if not os.path.exists(pk_df_path):
                continue

            pk_df = pl.read_csv(pk_df_path,rechunk=False, try_parse_dates=True, ignore_errors=True)

            for pk_col in candidate_table["columns"]:
                # if not pk_col.get("is_primary_key"):
                #     continue

                if pk_col["data_type"] != fk_col_type:
                    continue

                pk_col_name = pk_col["name"]
                print(pk_col_name, fk_col_name)

                # Check inclusion via anti-join
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




def convert_datetime_to_str(obj):
    if isinstance(obj, dict):
        return {k: convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(v) for v in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

def convert_str_to_datetime(obj):
    if isinstance(obj, dict):
        return {k: convert_str_to_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_str_to_datetime(v) for v in obj]
    elif isinstance(obj, str) and ISO_DATE_RE.match(obj):
        try:
            return datetime.fromisoformat(obj)
        except ValueError:
            return obj
    else:
        return obj
    
# def save_relationships(from_table, fk_matches):
#     rel_path = f"data/{from_table}.relationships.json"
#     with open(rel_path, "w") as f:
#         json.dump(fk_matches, f, indent=2)
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


# def load_related_tables(table_name):
#     related_metadata = {}
#     rel_path = f"data/{table_name}.relationships.json"
    
#     if not os.path.exists(rel_path):
#         return {}

#     with open(f"data/{table_name}.json") as f:
#         related_metadata[table_name] = json.load(f)

#     with open(rel_path) as f:
#         rels = json.load(f)

#     for rel in rels:
#         to_table = rel["to_table"]
#         if to_table not in related_metadata:
#             try:
#                 with open(f"data/{to_table}.json") as f:
#                     related_metadata[to_table] = json.load(f)
#             except FileNotFoundError:
#                 continue

#     return related_metadata
