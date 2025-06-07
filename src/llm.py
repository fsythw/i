import streamlit as st
from google import genai
from src.models import MetadataNoRel, Metadata, Data
from src.prompts import generate_enrichment_prompt

client = genai.Client(api_key=st.secrets['google']["GENAI_API_KEY"])


def first_call(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": MetadataNoRel,
        },
    )
    return response.text

def second_call(all_metadata: list[Metadata]) -> str:
    prompt = generate_enrichment_prompt(all_metadata)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Data,
        },
    )
    return response.text
