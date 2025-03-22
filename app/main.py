from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import optimizer
import os
import logging
import logging.config
import time
from dotenv import load_dotenv

# Configure logging
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "inferprompt.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        }
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True
        },
        "app": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        }
    }
}

# Setup logging
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

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

# Performance monitoring middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        # Log request details for non-static resources
        if not request.url.path.startswith(("/static/", "/docs", "/redoc", "/openapi.json")):
            logger.info(f"Request: {request.method} {request.url.path} - Completed in {process_time:.3f}s - Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request {request.method} {request.url.path}: {str(e)}")
        process_time = time.time() - start_time
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={"X-Process-Time": str(process_time)}
        )

# Include API routes
app.include_router(optimizer.router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to InferPrompt API",
        "documentation": "/docs",
        "version": "0.1.0"
    }


@app.on_event("startup")
async def startup_event():
    """Log when the server starts up"""
    logger.info("==================================================")
    logger.info("InferPrompt API server starting up")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Using OpenAI API: {bool(os.getenv('OPENAI_API_KEY'))}")
    logger.info(f"Default LLM model: {os.getenv('LLM_MODEL', 'gpt-3.5-turbo')}")
    logger.info("==================================================")


@app.on_event("shutdown")
async def shutdown_event():
    """Log when the server shuts down"""
    logger.info("InferPrompt API server shutting down")


if __name__ == "__main__":
    import uvicorn
    # Use environment variables or default values
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
