"""Main application file with FastAPI setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings, setup_logging, lifespan
from app.api.v1 import replays, topics, health

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Kafka Replay Tool API",
    description="API for replaying Kafka messages with enrichment and filtering.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# CORS Configuration
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],  # Adjust for your frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API Routers
app.include_router(replays.router, prefix="/api/v1")
app.include_router(topics.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Kafka Replay Tool API"}
