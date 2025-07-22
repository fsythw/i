import pymongo
import json
from pymongo import MongoClient, InsertOne
import streamlit as st
import os

@st.cache_resource
def get_mongo_client():

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI)
    return client


def add_to_database(metadata: dict, table_name: str):
    client = get_mongo_client()
    database = client["metadata"]
    collection = database[table_name]

    requesting = []

    requesting.append(InsertOne(metadata))

    collection.bulk_write(requesting)
