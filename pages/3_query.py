# import streamlit as st
# import asyncio

# from fastmcp import Client

# MCP_SERVER = "./server.py"

# st.header("3. query data")

# # 1) Build the client once
# client = Client(MCP_SERVER)

# def ask_llm(system_prompt: str, question: str) -> str:
#     """
#     Wrap the async call_tool into a sync function for Streamlit.
#     """
#     async def _call():
#         async with client:
#             # call our run_query tool on the server
#             result = await client.call_tool(
#                 "run_query",
#                 {
#                   "system_prompt": system_prompt,
#                   "user_question": question
#                 }
#             )
#             return result  # this is the raw string
#     return asyncio.run(_call())

# # 2) Streamlit UI
# query = st.text_input("Enter your question",
#                       placeholder="e.g. does ICU stay length decrease with patient age?")

# # Let the user customize or just default the system prompt
# sys_prompt = st.text_area(
#     "System Prompt",
#     value="You are a helpful assistant that can inspect table schemas "
#           "and write simple SQL-like plans."
# )

# if st.button("Run") and query:
#     with st.spinner("Thinking…"):
#         try:
#             answer = ask_llm(sys_prompt, query)
#             st.markdown("**LLM Answer:**")
#             st.write(answer)
#         except Exception as e:
#             st.error(f"Error while calling MCP server: {e}")
# pages/03_query.py
# import streamlit as st
# import asyncio
# from fastmcp import Client

# SERVER = "./server.py"   

# client = Client(SERVER)

# st.header("3. query data")
# query = st.text_input("Enter your question")
# sys_prompt = st.text_area(
#     "System Prompt",
#     value=(
#       "You are a data assistant.  "
#       "You have three tools available:\n"
#       "1) list_tables(): returns all table names.\n"
#       "2) get_schema(table): returns column→type map of that table.\n"
#       "3) preview(table, columns, n): returns n rows of those columns.\n\n"
#       "Use these tools as needed to figure out the answer."
#     )
# )

# if st.button("Run") and query:
#     with st.spinner("Thinking…"):
#         try:
#             # async def _run_agent():
#             #     async with client:
#             #         # this tells FastMCP: please use the LLM (you pick the model)
#             #         # to orchestrate calls to your registered tools
#             #         return await client.agent_run(
#             #             model="gemini-2.0-flash",
#             #             system=sys_prompt,
#             #             user=query,
#             #         )
#             # answer = asyncio.run(_run_agent())
#             # st.markdown("**Answer:**")
#             # st.write(answer)
#             async def call_tool(name: str):
#                 async with client:
#                     result = await client.call_tool("greet", {"name": name})
#                     print(result)

#             asyncio.run(call_tool(input("enter your name")))
 
#         except Exception as e:
#             st.error(f"Unexpected error: {e}")

import streamlit as st
import asyncio
import threading
import queue
import time
from dotenv import load_dotenv
import logging
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent_logic import setup_agent
from contextlib import contextmanager

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("streamlit_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# env file
logger.info("Loading environment variables from .env file...")
load_dotenv()

logger.info("Setting Streamlit page config and title.")
st.set_page_config(page_title="query", page_icon="💬")
st.title("3. query")

## streamlit does not support async so we need to find our own way
## background thread
class AsyncWorker:
    """worker thread for async operations"""
    
    def __init__(self):
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.loop = None
        
    def start(self):
        """start the worker thread"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
    
    def stop(self):
        """stop the worker thread"""
        if self.running:
            self.running = False
            self.request_queue.put(None)  # stop
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
    
    def _worker_loop(self):
        """main worker loop running in dedicated thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            while self.running:
                try:
                    
                    request = self.request_queue.get(timeout=1)
                    if request is None:  # stop signal
                        break
                    
                    request_id, coro = request
                    
                    try:
  
                        result = self.loop.run_until_complete(coro)
                        self.response_queue.put((request_id, 'success', result))
                    except Exception as e:
                        self.response_queue.put((request_id, 'error', str(e)))
                        
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Worker loop error: {e}")
                    
        finally:
            self.loop.close()
    
    def execute_async(self, coro, timeout=30):
        """execute async coroutine and wait"""
        if not self.running:
            self.start()
        
        request_id = id(coro)
        self.request_queue.put((request_id, coro))
        
        # wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=1)
                if response[0] == request_id:
                    status, result = response[1], response[2]
                    if status == 'success':
                        return result
                    else:
                        raise Exception(f"Async operation failed: {result}")
            except queue.Empty:
                continue
        
        raise TimeoutError(f"Async operation timed out after {timeout} seconds")

# initialize async worker
@st.cache_resource
def get_async_worker():
    return AsyncWorker()

async_worker = get_async_worker()

def setup_agent_sync():
    """synchronous wrapper for setup_agent"""
    return async_worker.execute_async(setup_agent())

def invoke_agent_sync(agent, messages, config):
    """synchronous wrapper for agent invocation"""
    return async_worker.execute_async(agent.ainvoke(messages, config))

logger.info("initializing Streamlit session state variables if not present.")
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'lc_history' not in st.session_state:
    st.session_state['lc_history'] = []
if 'agent' not in st.session_state:
    st.session_state['agent'] = None
if 'tools' not in st.session_state:
    st.session_state['tools'] = None
if 'client' not in st.session_state:
    st.session_state['client'] = None
if 'system_prompt' not in st.session_state:
    st.session_state['system_prompt'] = None
if 'initialization_error' not in st.session_state:
    st.session_state['initialization_error'] = None

# agent initialization
if st.session_state['agent'] is None and st.session_state['initialization_error'] is None:
    logger.info("Agent not found in session state. Initializing...")
    with st.spinner("Setting up MCP agent..."):
        try:
            client, tools, agent, system_prompt = setup_agent_sync()
            st.session_state['client'] = client
            st.session_state['tools'] = tools
            st.session_state['agent'] = agent
            st.session_state['system_prompt'] = system_prompt
            st.success("MCP agent ready!")
            logger.info("MCP agent setup complete and stored in session state.")
        except Exception as e:
            logger.error(f"Error setting up MCP agent: {e}")
            st.session_state['initialization_error'] = str(e)
            st.error(f"Failed to set up MCP agent: {e}")

# handle error
if st.session_state['initialization_error']:
    st.error(f"Initialization failed: {st.session_state['initialization_error']}")
    if st.button("Retry Initialization"):
        st.session_state['initialization_error'] = None
        st.rerun()

# show chat interface if agent is ready
if st.session_state['agent'] is not None:
    st.markdown("---")
    
    # actual user input text box
    user_input = st.text_area("Type your message:", key="user_input", height=100)
    col1, col2 = st.columns([1, 4])
    
    with col1:
        send_btn = st.button("Send", use_container_width=True)
    
    with col2:
        if st.session_state['chat_history']:
            clear_btn = st.button("Clear Chat", use_container_width=True)
            if clear_btn:
                st.session_state['chat_history'] = []
                st.session_state['lc_history'] = []
                st.rerun()

    if send_btn and user_input:
        logger.info(f"User submitted input: {user_input}")
        
        # add if first
        if len(st.session_state['lc_history']) == 0 and st.session_state['system_prompt']:
            st.session_state['lc_history'].append(SystemMessage(st.session_state['system_prompt']))
        
        # add HumanMessage to LC history
        st.session_state['lc_history'].append(HumanMessage(user_input))
        st.session_state['chat_history'].append(("user", user_input))
        
        with st.spinner("Agent is thinking..."):
            try:
                logger.info("Invoking agent with chat history...")
                config = {
                    "configurable": {
                        "thread_id": "main_conversation",
                        "checkpoint_id": None
                    }
                }
                response = invoke_agent_sync(
                    st.session_state['agent'],
                    {"messages": st.session_state['lc_history']}, 
                    config
                )
                logger.info(f"Agent response: {response}")
                
                if isinstance(response, dict) and "messages" in response and response["messages"]:
                    last_msg = response["messages"][-1]
                    reply = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                    st.session_state['lc_history'].append(AIMessage(reply))
                    st.session_state['chat_history'].append(("assistant", reply))
                else:
                    logger.info(f"Agent response (non-dict): {response}")
                    st.session_state['lc_history'].append(AIMessage(str(response)))
                    st.session_state['chat_history'].append(("assistant", str(response)))
            except Exception as e:
                logger.error(f"Error during agent invocation: {e}")
                st.session_state['chat_history'].append(("assistant", f"Error: {e}"))
        
        st.rerun()

    # display chat history
    st.markdown("---")
    if st.session_state['chat_history']:
        for sender, msg in st.session_state['chat_history']:
            if sender == "user":
                st.markdown(f"<div style='text-align:right; color:#1a73e8; margin-bottom: 10px;'><b>You:</b> {msg}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:left; color:#34a853; margin-bottom: 10px;'><b>Assistant:</b> {msg}</div>", unsafe_allow_html=True)
    else:
        st.info("Start a conversation by typing a message above!")

# garbage
import atexit
atexit.register(lambda: async_worker.stop())