import streamlit as st
import os
import json
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





# def build_relationship_graph(metadata):
#     graph = defaultdict(list)
#     for table in metadata:
#         for rel in table.get("relationships", []):
#             graph[table["table_name"]].append(rel["to_table"])
#     return graph

# def find_related_tables(start_table, graph, depth=2):
#     visited = set()
#     queue = deque([(start_table, 0)])
#     while queue:
#         table, level = queue.popleft()
#         if level > depth or table in visited:
#             continue
#         visited.add(table)
#         for neighbor in graph[table]:
#             queue.append((neighbor, level + 1))
#     return visited

# def convert_to_er_graphviz(metadata: list[dict], focus_table=None, degree=2) -> str:
#     graph = build_relationship_graph(metadata)
#     tables_to_show = set(t["table_name"] for t in metadata)

#     if focus_table:
#         tables_to_show = find_related_tables(focus_table, graph, depth=degree)

#     lines = ["digraph ER {", "  rankdir=LR;", '  node [shape=record, fontsize=10];']

#     for table in metadata:
#         if table["table_name"] not in tables_to_show:
#             continue
#         col_lines = []
#         for col in table["columns"]:
#             prefix = "<PK> " if col.get("is_primary_key") else ""
#             col_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
#         table_def = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(col_lines)}\\l}}"];'
#         lines.append(f"  {table_def}")

#     for table in metadata:
#         if table["table_name"] not in tables_to_show:
#             continue
#         for rel in table.get("relationships", []):
#             if rel["to_table"] not in tables_to_show:
#                 continue
#             lines.append(f'  {table["table_name"]} -> {rel["to_table"]} [label="{rel["from_column"]} → {rel["to_column"]}"];')

#     lines.append("}")
#     return "\n".join(lines)


# def convert_to_er_graphviz(enriched_table: dict, data_dir: str = "data") -> str:
#     lines = ["digraph ER {", "  rankdir=LR;", '  node [shape=record, fontsize=10];']

#     visited_tables = {}
#     to_visit = {enriched_table["table_name"]: enriched_table}

#     # Load related tables based on relationships
#     for rel in enriched_table.get("relationships", []):
#         related_table_name = rel["to_table"]
#         rel_path = os.path.join(data_dir, f"{related_table_name}.json")
#         if os.path.exists(rel_path):
#             with open(rel_path, "r") as f:
#                 related_table = json.load(f)
#                 to_visit[related_table_name] = related_table

#     # Draw nodes
#     for table in to_visit.values():
#         visited_tables[table["table_name"]] = True
#         column_lines = []
#         for col in table["columns"]:
#             prefix = "<PK> " if col.get("is_primary_key") else ""
#             column_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
#         label = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(column_lines)}\\l}}"];'
#         lines.append(f"  {label}")

#     # Draw edges from original table’s relationships
#     for rel in enriched_table.get("relationships", []):
#         from_table = enriched_table["table_name"]
#         to_table = rel["to_table"]
#         from_col = rel["from_column"]
#         to_col = rel["to_column"]
#         label = rel.get("reason", "")
#         lines.append(f'  {from_table} -> {to_table} [label="{from_col} → {to_col}", tooltip="{label}"];')

#     lines.append("}")
#     return "\n".join(lines)

# def load_table_metadata(table_name, data_dir="data"):
#     file_path = os.path.join(data_dir, f"{table_name}.json")
#     if os.path.exists(file_path):
#         with open(file_path, "r") as f:
#             return json.load(f)
#     return None

# def collect_related_metadata(focus_table, degree=1, data_dir="data"):
#     visited = set()
#     to_visit = [(focus_table, 0)]
#     all_metadata = {}

#     while to_visit:
#         current_table, depth = to_visit.pop(0)
#         if current_table in visited or depth > degree:
#             continue

#         metadata = load_table_metadata(current_table, data_dir)
#         if not metadata:
#             continue

#         visited.add(current_table)
#         all_metadata[current_table] = metadata

#         for rel in metadata.get("relationships", []):
#             neighbor_tables = [rel["to_table"], rel["from_table"]]
#             for neighbor in neighbor_tables:
#                 if neighbor not in visited:
#                     to_visit.append((neighbor, depth + 1))

#     return list(all_metadata.values())

# def convert_to_er_graphviz(target_table: dict, related_tables: list[dict]) -> str:
# def convert_to_er_graphviz(enriched: list[dict]) -> str:
#     lines = [
#         "digraph ER {",
#         "  rankdir=LR;",
#         '  node [shape=record, fontsize=10];'
#     ]

#     # Combine all tables: target + similar
#     # all_tables = [target_table] + related_tables
#     # print(all_tables)
#     table_map = {table["table_name"]: table for table in enriched}

#     # Draw table nodes
#     # for table in all_tables:
#     #     column_lines = [
#     #         f"{'<PK> ' if col.get('is_primary_key') else ''}{col['name']}: {col['data_type']}"
#     #         for col in table["columns"]
#     #     ]
#     #     label = "\\l".join(column_lines) + "\\l"
#     #     lines.append(f'  {table["table_name"]} [label="{{{table["table_name"]}|{label}}}"];')
#     for table in enriched:
#         column_lines = []
#         for col in table["columns"]:
#             prefix = "<PK> " if col.get("is_primary_key") else ""
#             column_lines.append(f"{prefix}{col['name']}: {col['data_type']}")
#         table_def = f'{table["table_name"]} [label="{{{table["table_name"]}|{"\\l".join(column_lines)}\\l}}"];'
#         lines.append(f"  {table_def}")

#     for table in enriched:
#         if table["table_name"] not in table_map:
#             continue
#         for rel in table.get("relationships", []):
#             if rel["to_table"] not in table_map:
#                 continue
#             from_table = table["table_name"]
#             to_table = rel["to_table"]
#             from_col = rel["from_column"]
#             to_col = rel["to_column"]
#             label = rel.get("reason", "")
#             lines.append(f'  {from_table} -> {to_table} [label="{from_col} → {to_col}", tooltip="{label}"];')
    
#     lines.append("}")
#     return "\n".join(lines)


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