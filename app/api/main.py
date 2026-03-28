from fastapi import FastAPI

app = FastAPI(
    title="Price Audit Copilot",
    description="Week 1 minimal runnable skeleton",
    version="0.1.0"
)


@app.get("/")
def root():
    return {"message": "Price Audit Copilot API is running."}
