from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import optimizer
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="InferPrompt API",
    description="ASP-based LLM prompt optimization framework",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(optimizer.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to InferPrompt API",
        "documentation": "/docs",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    # Use environment variables or default values
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
