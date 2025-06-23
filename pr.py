import polars

df = polars.read_csv("C:\\Users\\faith\\Downloads\\data\\1\\PATIENTS.csv", ignore_errors=True, rechunk=False, try_parse_dates=True)

print(df["GENDER"].null_count())