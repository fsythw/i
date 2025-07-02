import pymongo
import json
from pymongo import MongoClient, InsertOne
import streamlit as st

@st.cache_resource
def get_mongo_client():
    return pymongo.MongoClient(st.secrets["mongo"]["URI"])


# client = pymongo.MongoClient("mongodb+srv://faithwansy123:rhbc1234@cluster0.oxan1it.mongodb.net/")
# db = client.metadata
# collection = db.ADMISSIONS
# requesting = []

# with open(r"./data/ADMISSIONS.json") as f:
#     data = json.load(f)
#     requesting.append(InsertOne(data))



# def add_to_database(metadata: dict):
#     data = json.dump(metadata)
#     requesting.append(InsertOne(data))

# result = collection.bulk_write(requesting)
# client.close()