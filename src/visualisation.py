import streamlit as st
from graphviz import Digraph

def render_er_diagram(metadata):
    dot = Digraph(comment="ER Diagram")
    dot.attr(rankdir='LR') #CHANGE LAYOUT

    for table in metadata:
        label = f"<<TABLE BORDER='1' CELLBORDER='0' CELLSPACING='0'>"
        label += f"<TR><TD BGCOLOR='lightblue'><B>{table['table_name']}</B></TD></TR>"

        for col in table['columns']:
            prefix = '🔑 ' if col['is_primary_key'] else ''
            label += f"<TR><TD ALIGN='LEFT'>{prefix}{col['name']} ({col['data_type']})</TD></TR>"

        label += "</TABLE>>"
        dot.node(table['table_name'], label=label, shape='plaintext')

    for table in metadata:
        for rel in table.get("relationships", []):
            dot.edge(rel['from_table'], rel['to_table'], label=f"{rel['from_column']} ➝ {rel['to_column']}")

    return dot
