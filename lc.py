## pip install langchain_google_genai
import streamlit ##.env

from langchain_google_genai import ChatGoogleGenerativeAI

lc = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=streamlit.secrets['google']["GENAI_API_KEY"])
try:
    response = lc.invoke("What is 1+1?")
    print("Model invoked successfully:", response)
except Exception as e:
    print(f"Error invoking model: {e}")