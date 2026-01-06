from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import auth, products, tasks, shopify, ai, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting AMTS Backend...")
    yield
    # Shutdown
    print("Shutting down AMTS Backend...")


app = FastAPI(
    title="AMTS Backend API",
    description="Advanced Marketing Theme System - Backend API for cannabis e-commerce SaaS",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(shopify.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "AMTS Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api")
async def api_info():
    return {
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "products": "/api/products",
            "tasks": "/api/tasks",
            "shopify": "/api/shopify",
            "ai": "/api/ai",
        }
    }

