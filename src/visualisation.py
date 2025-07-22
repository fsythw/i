import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque


def convert_to_er_graphviz(metadata: list[dict]) -> str:
    lines = ["digraph ER {", "  rankdir=LR;", '  node [shape=record, fontsize=10];']

    # Define nodes (tables with their columns)
    for table in metadata:
        column_lines = []
        for col in table["columns"]:
            prefix = "<PK> " if col.get("is_primary_key") else ""
            column_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
        table_def = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(column_lines)}\\l}}"];'
        lines.append(f"  {table_def}")

    # Define relationships
    for table in metadata:
        for rel in table.get("relationships", []):
            from_table = table["table_name"]
            to_table = rel["to_table"]
            from_col = rel["from_column"]
            to_col = rel["to_column"]
            label = rel.get("reason", "")
            lines.append(f'  {from_table} -> {to_table} [label="{from_col} → {to_col}", tooltip="{label}"];')

    lines.append("}")
    return "\n".join(lines)