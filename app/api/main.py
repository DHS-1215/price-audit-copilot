from fastapi import FastAPI, HTTPException
from app.core.llm_ollama import ask_llm, extract_product
from app.core.schemas import (
    AskRequest,
    AskResponse,
    ExtractRequest,
    ProductExtractResult,
)

app = FastAPI(
    title="Price Audit Copilot",
    description="Week 1 minimal runnable skeleton",
    version="0.1.0"
)


@app.get("/")
def root():
    return {"message": "Price Audit Copilot API is running."}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        answer = ask_llm(req.question)
        return AskResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/extract', response_model=ProductExtractResult)
def extract(req: ExtractRequest):
    try:
        result = extract_product(req.title)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
