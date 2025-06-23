import itertools
import polars as pl

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
        (table["table_name"], col["name"]): set(col["unique_values"])
        for table in metadata
        for col in table["columns"]
        if col.get("is_primary_key")
    }

    for table in metadata:
        for col in table["columns"]:
            if col.get("is_primary_key"):
                continue  # skip PKs
            fk_vals = set(col.get("unique_values", []))
            if not fk_vals:
                continue

            for (pk_table, pk_col), pk_vals in pk_index.items():
                if not pk_vals:
                    continue
                unmatched = fk_vals - pk_vals
                match_ratio = 1 - len(unmatched) / max(len(fk_vals), 1) 

                if match_ratio >= (1 - error_threshold):
                    fk_candidates.append({
                        "from_table": table["table_name"],
                        "from_column": col["name"],
                        "to_table": pk_table,
                        "to_column": pk_col,
                        "match_ratio": match_ratio
                    })

    return fk_candidates #list
