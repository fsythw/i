import streamlit as st
from graphviz import Digraph
from collections import defaultdict, deque

# def render_er_diagram(metadata):
#     dot = Digraph(comment="ER Diagram")
#     dot.attr(rankdir='LR') #CHANGE LAYOUT

#     for table in metadata:
#         label = f"<<TABLE BORDER='1' CELLBORDER='0' CELLSPACING='0'>"
#         label += f"<TR><TD BGCOLOR='lightblue'><B>{table['table_name']}</B></TD></TR>"

#         for col in table['columns']:
#             prefix = '🔑 ' if col['is_primary_key'] else ''
#             label += f"<TR><TD ALIGN='LEFT'>{prefix}{col['name']} ({col['data_type']})</TD></TR>"

#         label += "</TABLE>>"
#         dot.node(table['table_name'], label=label, shape='plaintext')

#     for table in metadata:
#         for rel in table.get("relationships", []):
#             dot.edge(rel['from_table'], rel['to_table'], label=f"{rel['from_column']} ➝ {rel['to_column']}")

#     return dot

# def convert_to_er_graphviz(metadata: list[dict]) -> str:
#     lines = ["digraph ER {", "  rankdir=LR;", '  node [shape=record, fontsize=10];']

#     # Define nodes (tables with their columns)
#     for table in metadata:
#         column_lines = []
#         for col in table["columns"]:
#             prefix = "<PK> " if col.get("is_primary_key") else ""
#             column_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
#         table_def = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(column_lines)}\\l}}"];'
#         lines.append(f"  {table_def}")

#     # Define relationships
#     for table in metadata:
#         for rel in table.get("relationships", []):
#             from_table = table["table_name"]
#             to_table = rel["to_table"]
#             from_col = rel["from_column"]
#             to_col = rel["to_column"]
#             label = rel.get("reason", "")
#             lines.append(f'  {from_table} -> {to_table} [label="{from_col} → {to_col}", tooltip="{label}"];')

#     lines.append("}")
#     return "\n".join(lines)



def build_relationship_graph(metadata):
    graph = defaultdict(list)
    for table in metadata:
        for rel in table.get("relationships", []):
            graph[table["table_name"]].append(rel["to_table"])
    return graph

def find_related_tables(start_table, graph, depth=2):
    visited = set()
    queue = deque([(start_table, 0)])
    while queue:
        table, level = queue.popleft()
        if level > depth or table in visited:
            continue
        visited.add(table)
        for neighbor in graph[table]:
            queue.append((neighbor, level + 1))
    return visited

def convert_to_er_graphviz(metadata: list[dict], focus_table=None, degree=2) -> str:
    graph = build_relationship_graph(metadata)
    tables_to_show = set(t["table_name"] for t in metadata)

    if focus_table:
        tables_to_show = find_related_tables(focus_table, graph, depth=degree)

    lines = ["digraph ER {", "  rankdir=LR;", '  node [shape=record, fontsize=10];']

    for table in metadata:
        if table["table_name"] not in tables_to_show:
            continue
        col_lines = []
        for col in table["columns"]:
            prefix = "<PK> " if col.get("is_primary_key") else ""
            col_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
        table_def = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(col_lines)}\\l}}"];'
        lines.append(f"  {table_def}")

    for table in metadata:
        if table["table_name"] not in tables_to_show:
            continue
        for rel in table.get("relationships", []):
            if rel["to_table"] not in tables_to_show:
                continue
            lines.append(f'  {table["table_name"]} -> {rel["to_table"]} [label="{rel["from_column"]} → {rel["to_column"]}"];')

    lines.append("}")
    return "\n".join(lines)
