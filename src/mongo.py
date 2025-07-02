import pymongo
import json
from pymongo import MongoClient, InsertOne

client = pymongo.MongoClient("mongodb+srv://faithwansy123:rhbc1234@cluster0.oxan1it.mongodb.net/")
db = client.metadata
collection = db.ADMISSIONS
requesting = []

with open(r"./data/ADMISSIONS.json") as f:
    data = json.load(f)
    requesting.append(InsertOne(data))

result = collection.bulk_write(requesting)
client.close()