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


class TestAdjacencyWithRoadDetectionRequest(BaseModel):
    address1: str
    address2: str


class TestAdjacencyWithRoadDetectionResponse(BaseModel):
    adjacent: bool
    same_side_of_street: bool
    no_road_crossing: bool
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


@router.post("/test_adjacency_with_road_detection", response_model=TestAdjacencyWithRoadDetectionResponse)
async def test_adjacency_with_road_detection(request: TestAdjacencyWithRoadDetectionRequest):
    """
    Test if two addresses are connected without crossing a drivable road.
    Only road crossing and distance are checked.
    """
    from geopy.distance import geodesic

    # Geocode both addresses
    coords1 = mapbox_service.geocode_address(request.address1)
    coords2 = mapbox_service.geocode_address(request.address2)

    if not coords1 or not coords2:
        raise HTTPException(status_code=400, detail="Could not geocode one or both addresses")

    lat1, lng1 = coords1
    lat2, lng2 = coords2

    # Calculate distance
    distance = geodesic((lat1, lng1), (lat2, lng2)).miles

    # Check if accessible without crossing roads
    no_road_crossing = mapbox_service.is_accessible_without_crossing_road(
        (lat1, lng1), (lat2, lng2)
    )

    message = f"Distance: {distance:.4f} miles"
    if no_road_crossing:
        message += ", No road crossing detected"
    else:
        message += ", Road crossing detected"

    return TestAdjacencyWithRoadDetectionResponse(
        adjacent=no_road_crossing,
        same_side_of_street=False,
        no_road_crossing=no_road_crossing,
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