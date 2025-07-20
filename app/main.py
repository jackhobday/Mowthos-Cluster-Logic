from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import clusters
from app.database import engine
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Mowthos Cluster Logic",
    description="FastAPI microservice for managing robotic mowing clusters",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clusters.router)


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Mowthos Cluster Logic API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "register_host": "/clusters/register_host_home",
            "join_cluster": "/clusters/join_cluster",
            "get_clusters": "/clusters/",
            "get_cluster": "/clusters/{cluster_id}",
            "mower_status": "/clusters/{cluster_id}/mower"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "service": "mowthos-cluster-logic"} 