import numpy as np
import json
import streamlit as st
from typing import List, Dict
from google import genai

client = genai.Client(api_key=st.secrets['google']["GENAI_API_KEY"])

def get_embedding(text: str) -> List[float]:
    response = client.models.embed_content(
        model="embedding-001",
        contents=text,

    )
    return response.embeddings[0].values


def cosine_sim(a: List[float], b: List[float]) -> float:
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_similar_tables(target_table: Dict, all_tables: List[Dict], top_n: int = 5) -> List[Dict]:
    target_text = target_table["description"]
    target_embedding = get_embedding(target_text)

    scored = []
    for table in all_tables:
        if table["table_name"] == target_table["table_name"]:
            continue
        other_embedding = get_embedding(table["description"])
        score = cosine_sim(target_embedding, other_embedding)
        scored.append((score, table))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [table for _, table in scored[:top_n]]
