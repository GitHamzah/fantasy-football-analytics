"""Fantasy Football Analytics API.

Built with FastAPI. Serves player stats, fantasy leaders, projections,
and AI-powered analysis from a SQL Server warehouse.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import players, stats, leaders, ai, analytics, projections, advanced, formations

app = FastAPI(
    title="Fantasy Football Analytics API",
    description=(
        "Free fantasy football analytics powered by nflverse data. "
        "Supports Standard, Half-PPR, and PPR scoring formats. "
        "Includes projections and AI-powered natural language Q&A."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router)
app.include_router(stats.router)
app.include_router(leaders.router)
app.include_router(analytics.router)
app.include_router(projections.router)
app.include_router(advanced.router)
app.include_router(formations.router)
app.include_router(ai.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "name": "Fantasy Football Analytics API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }
