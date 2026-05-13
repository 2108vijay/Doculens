"""
main.py — DocuLens V2 FastAPI Server
Run: uvicorn main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.database import init_db
from api.classifier import get_classifier
from api.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting DocuLens V2...")
    await init_db()
    try:
        get_classifier()
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
    try:
        get_storage()
    except Exception as e:
        print(f"⚠️  MinIO: {e}")
    yield
    print("👋 Stopped")


app = FastAPI(
    title="DocuLens API V2",
    description="Classify Aadhaar / PAN / Other document images. Each upload gets a sequential ID (1, 2, 3...).",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
async def root():
    return {"service": "DocuLens API", "version": "2.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
