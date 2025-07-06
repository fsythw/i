from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# mongo
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
metadata_db = client["metadata"]

mcp = FastMCP("Hospital Metadata MCP Server")

@mcp.tool()
def list_tables() -> List[str]:
    """
    List all available tables (collections) in the metadata database.
    Use this to discover which tables contain information about patients, admissions, demographics, and hospital stays.
    """
    return metadata_db.list_collection_names()

@mcp.tool()
def get_schema(table: str) -> Optional[dict]:
    """
    Get the schema (column names and types) for a given table in the metadata database.
    Use this to understand what fields are available for analysis, such as age, gender, admission dates, and length of stay.
    This helps answer questions about relationships between different fields.
    """
    doc = metadata_db[table].find_one({}, {"_id": 0, "columns": 1})
    if doc and "columns" in doc:
        return {"columns": doc["columns"]}
    return None

@mcp.tool()
def get_description(table: str) -> Optional[str]:
    """
    Get a human-readable description of a table in the metadata database.
    This helps you understand what kind of data is stored in each table.
    """
    doc = metadata_db[table].find_one({}, {"_id": 0, "description": 1})
    if doc and "description" in doc:
        return doc["description"]
    return None


if __name__ == "__main__":
    print("Connecting to MongoDB at", MONGO_URI)
    print("Available tables:", list_tables())
    mcp.run(transport="streamable-http")