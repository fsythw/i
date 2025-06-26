import polars as pl

# df = polars.read_csv("C:\\Users\\faith\\Downloads\\data\\1\\PATIENTS.csv", ignore_errors=True, rechunk=False, try_parse_dates=True)

# print(df["GENDER"].null_count())

# Create two sample DataFrames
df1 = pl.DataFrame({
    "id_1": [1, 2, 3],
    "value": ["A", "B", "C"]
})

df2 = pl.DataFrame({
    "id_2": [1, 2, 3, 4, 6, 7],
    "value": ["A", "B", "C", "D", "F", "G"]
})

# Perform the set difference (df1 - df2) using an anti-join
# The 'on' parameter specifies the column(s) to join on.
# The 'how="anti"' ensures only rows from df1 with no match in df2 are returned.
set_difference_df = df1.join(df2, left_on="id_1", right_on="id_2", how="anti").to_dicts()
print(set_difference_df)

if not set_difference_df:
    print("hi")
else:
    print("hello")

## df1 is a subset of df2