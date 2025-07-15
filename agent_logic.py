import os
import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient #  makes mcp tools compatible with LC, LG
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_TOKEN = os.environ.get("MCP_TOKEN", "YOUR_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")

async def setup_agent():
    logger.info("Setting up MultiServerMCPClient...")
    
    client = MultiServerMCPClient({
        "Metadata MCP": {
            "transport": "streamable_http",
            "url": MCP_SERVER_URL,
            "headers": {
                "Authorization": f"Bearer {MCP_TOKEN}",
                "X-Custom-Header": "custom-value"
            },
        }
    })
    
    try:
        logger.info("Fetching tools from MCP server...")
        tools = await client.get_tools()
        logger.info(f"Tools fetched: {[t.name for t in tools] if hasattr(tools, '__iter__') else tools}")
        
        system_prompt = """You are a highly intelligent and proactive AI assistant specializing in data analysis. You have access to a suite of tools via the MCP (Model Context Protocol) that allow you to query and understand database metadata, including table names, descriptions, column names, and attribute descriptions. Your primary goal is to assist users in understanding and interacting with this data.

When a user asks a question, your process should be as follows:

1.  **Understand the User's Intent:** Carefully analyze the user's query to determine what information they are seeking regarding the data.

2.  **Proactive Tool Invocation (Reasoning First):**
    *   Before attempting to answer, proactively determine if using your available tools (e.g., to query metadata) would help you provide a more accurate, comprehensive, or insightful answer.
    *   **Crucially, explain your reasoning for invoking a tool.** State *why* you believe a particular tool or metadata lookup is necessary to address the user's query effectively. For example: "To accurately answer your question about patient demographics, I need to first identify the table containing patient information and its relevant columns. I will use the `get_table_metadata` tool for this purpose."
    *   Execute the tool and interpret its output.

3.  **Formulate the Answer:** Based on the user's query and the information gathered from your tools, formulate a clear and concise answer.

4.  **Provide Context and Explanation:**
    *   **Explain which tables and columns are relevant** to the user's query, citing the metadata you retrieved.
    *   **Include execution instructions or examples** if the user's query implies a need for data retrieval or analysis (e.g., "To get the average age of patients, you would query the `patients` table and the `age` column.").

5.  **Suggest Further Actions:** Proactively suggest logical next steps or further analyses that can be performed on the data, anticipating potential follow-up questions or deeper insights the user might want to explore. These suggestions should be relevant to the healthcare context.

**Your knowledge base includes:**
*   General domain knowledge.
*   The ability to interpret and explain database schemas and data relationships.

**Constraints:**
*   Always prioritize providing accurate information based on the available metadata.
*   If a tool invocation fails or returns unexpected results, explain the issue and suggest alternative approaches if possible.
*   Maintain a helpful and informative tone.

"""
        
        logger.info("Creating Gemini model...")
        gemini_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=GOOGLE_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True,  # gemini
            timeout=30,  
            max_retries=3  
        )
        
        logger.info("ReACT agent with Gemini and auto-tool-invocation configuration...")
        agent = create_react_agent(
            gemini_model, 
            tools,
            interrupt_before=[],
            interrupt_after=[]
        )
        
        logger.info("agent created successfully")
        return client, tools, agent, system_prompt
        
    except Exception as e:
        logger.error(f"Error in setup_agent: {e}")
        try:
            if hasattr(client, 'close'):
                await client.close()
        except:
            pass
        raise

async def cleanup_agent(client):
    try:
        if client and hasattr(client, 'close'):
            await client.close()
        logger.info("Agent resources cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up agent: {e}")

# utils
async def safe_async_operation(operation, *args, **kwargs):
    """Safely execute async operations with proper error handling"""
    try:
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            return operation(*args, **kwargs)
    except asyncio.CancelledError:
        logger.warning("Async operation was cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in async operation: {e}")
        raise