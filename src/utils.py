import itertools
import polars as pl
from datetime import datetime
import re 
import hashlib 

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

def find_inclusion_dependencies_from_metadata(metadata, error_threshold=0.1):
    fk_candidates = []

    pk_index = {
        (table["table_name"], col["name"]): col
        for table in metadata
        for col in table["columns"]
        if col.get("is_primary_key")
    }

    for table in metadata:
        for col in table["columns"]:
            if col.get("is_primary_key"):
                continue
            fk_min, fk_max = col.get("min"), col.get("max")
            fk_name = col["name"]
            fk_table = table["table_name"]

            for (pk_table, pk_col), pk_meta in pk_index.items():
                pk_min, pk_max = pk_meta.get("min"), pk_meta.get("max")

                # If any min/max missing, skip
                if None in [fk_min, fk_max, pk_min, pk_max]:
                    continue

                if fk_min >= pk_min and fk_max <= pk_max:
                    fk_candidates.append({
                        "from_table": fk_table,
                        "from_column": fk_name,
                        "to_table": pk_table,
                        "to_column": pk_col,
                        "match_type": "range_inclusion"
                    })

    return fk_candidates


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
    
