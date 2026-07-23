import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from .db.db import create_db_and_tables, close_db

# Import routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Creating database tables...")
        await create_db_and_tables()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    yield
    try:
        print("Closing database connections...")
        await close_db()
        print("Database connections closed successfully!")
    except Exception as e:
        print(f"Error closing database: {e}")  
    

app = FastAPI(
    lifespan=lifespan,
    title="Auto-Inspect Kenya API",
    description="Young Auto Inspection System "
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)