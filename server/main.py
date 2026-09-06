"""Epic Client backend entry point.

Run from the server/ folder:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401  (import so tables register on Base)
from routers import users, apps

# Create tables on startup (fine for SQLite / early development).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Epic Client Store API", version="0.1.0")

# Allow a website (e.g. a Lovable build) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten to your site's domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(apps.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Epic Client store backend is running"}
