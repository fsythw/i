## install requirements python 3.12.1

```bash
pip install -r requirements.txt
```


## api keys
create .env file 

MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/
GOOGLE_API_KEY=your-google-api-key
GEMINI_API_KEY=your-gemini-api-key

## start mcp server
```bash
python server.py
```

## run app
```bash
streamlit run app.py
```