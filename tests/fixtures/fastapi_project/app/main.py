from fastapi import FastAPI

app = FastAPI(title="Sample API")

@app.get("/")
def read_root():
    return {"message": "Hello World"}
