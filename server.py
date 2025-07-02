from fastmcp import FastMCP

mcp = FastMCP("test")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
def retrieve_table_names() -> str:
    return 


if __name__ == "__main__":
    mcp.run()

