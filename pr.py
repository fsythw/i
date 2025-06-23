import polars

df = polars.read_csv("C:\\Users\\admin\\Downloads\\1\\PATIENTS.csv", ignore_errors=True, rechunk=False, try_parse_dates=True)

print(df["DOB"].drop_nulls().unique().to_list())