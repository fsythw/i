# monocerose

mcp client & server that is basically amazon Q on a budget

supports metadata generation using statistical profiling in polars (foreign key discovery is hard!) and LLM-as-a-judge, and natural language querying with a ReACT agent. frontend using streamlit with workaround for async operations.

<img width="1276" height="576" alt="Screenshot 2026-06-27 at 7 06 38 PM" src="https://github.com/user-attachments/assets/b126b0da-c0c5-4133-aa9b-1040a055fc50" />



## install requirements python 3.12.1

```bash
pip install -r requirements.txt
```


## api keys
create .env file 

MONGO_URI=mongodb+srv://username:password@cluster-url/

GOOGLE_API_KEY=your-google-api-key

GEMINI_API_KEY=your-gemini-api-key

## start mcp server
```bash
python server.py
```

## run app
in a separate terminal run 

```bash
streamlit run app.py
```
