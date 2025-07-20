from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.schemas import (
    HostRegistrationRequest, 
    JoinClusterRequest, 
    ClusterAssignmentResponse,
    ClusterResponse,
    MowerStatusResponse
)
from app.services.cluster_service import cluster_service
from app.services.mapbox_service import MapboxService
from app.config import settings
from app.models import Cluster

router = APIRouter(prefix="/clusters", tags=["clusters"])

# Create MapboxService instance
mapbox_service = MapboxService(settings.mapbox_access_token)


class GeocodeRequest(BaseModel):
    address: str


class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    address: str


class TestAdjacencyRequest(BaseModel):
    lat1: float
    lng1: float
    lat2: float
    lng2: float


class TestAdjacencyResponse(BaseModel):
    adjacent: bool
    road_barrier: bool
    distance_miles: float
    message: str


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(request: GeocodeRequest):
    """
    Geocode an address to get latitude and longitude coordinates.
    """
    coordinates = mapbox_service.geocode_address(request.address)
    
    if not coordinates:
        raise HTTPException(status_code=404, detail="Address not found")
    
    lat, lon = coordinates
    return GeocodeResponse(
        latitude=lat,
        longitude=lon,
        address=request.address
    )


@router.post("/test_adjacency", response_model=TestAdjacencyResponse)
async def test_adjacency(request: TestAdjacencyRequest):
    """
    Test adjacency between two coordinates, including road barrier detection.
    """
    from geopy.distance import geodesic
    
    # Calculate distance
    distance = geodesic((request.lat1, request.lng1), (request.lat2, request.lng2)).miles
    
    # Check if addresses are adjacent (proximity + no road barrier)
    adjacent = mapbox_service.are_addresses_contiguously_adjacent(
        request.lat1, request.lng1, request.lat2, request.lng2
    )
    
    # Check specifically for road barrier
    road_barrier = mapbox_service.check_road_barrier(
        request.lat1, request.lng1, request.lat2, request.lng2
    )
    
    message = f"Distance: {distance:.4f} miles"
    if road_barrier:
        message += ", Road barrier detected"
    else:
        message += ", No road barrier"
    
    return TestAdjacencyResponse(
        adjacent=adjacent,
        road_barrier=road_barrier,
        distance_miles=distance,
        message=message
    )


@router.post("/register_host_home", response_model=ClusterAssignmentResponse)
async def register_host_home(
    request: HostRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new host home and create a new cluster.
    """
    result = cluster_service.register_host_home(db, request)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.post("/join_cluster", response_model=ClusterAssignmentResponse)
async def join_cluster(
    request: JoinClusterRequest,
    db: Session = Depends(get_db)
):
    """
    Assign a non-host user to the closest eligible cluster with valid adjacency.
    """
    result = cluster_service.join_cluster(db, request)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.get("/", response_model=List[ClusterResponse])
async def get_all_clusters(db: Session = Depends(get_db)):
    """
    Get all clusters with their users.
    """
    clusters = cluster_service.get_all_clusters(db)
    return clusters


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific cluster.
    """
    cluster = cluster_service.get_cluster_info(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.get("/{cluster_id}/mower", response_model=MowerStatusResponse)
async def get_mower_status(cluster_id: int, db: Session = Depends(get_db)):
    """
    Get mower status for a specific cluster.
    This is a stub endpoint for future PyMammation integration.
    """
    # Check if cluster exists
    cluster = cluster_service.get_cluster_info(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Mock mower status response
    # In a real implementation, this would integrate with PyMammation
    from datetime import datetime
    
    return MowerStatusResponse(
        cluster_id=cluster_id,
        status="idle",  # Mock status
        current_location=None,
        battery_level=85.0,  # Mock battery level
        last_updated=datetime.now()
    ) 