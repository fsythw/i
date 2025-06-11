import polars

df = polars.read_csv("C:\\Users\\admin\\Downloads\\1\\ICUSTAYS.csv", ignore_errors=True, rechunk=False, try_parse_dates=True)

total_rows = len(df)

unique_counts = df.select(polars.all().n_unique())

unique_columns = []
for column in df.columns:
    unique_count = unique_counts.select(polars.col(column)).item()
    if unique_count == total_rows:
        unique_columns.append(column)

print(unique_columns)

print(df.schema.keys(), df.schema.values())

## pandas
## d.nunique()
## convert_dtypes() for best data type
