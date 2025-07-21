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


class TestAdjacencyWithStreetRequest(BaseModel):
    address1: str
    address2: str


class TestAdjacencyWithStreetResponse(BaseModel):
    adjacent: bool
    same_side_of_street: bool
    distance_miles: float
    message: str


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


@router.post("/test_adjacency_with_street", response_model=TestAdjacencyWithStreetResponse)
async def test_adjacency_with_street(request: TestAdjacencyWithStreetRequest):
    """
    Test if two addresses are adjacent, including side-of-street logic.
    This combines proximity check with odd/even house number parity.
    """
    # Geocode both addresses
    coords1 = mapbox_service.geocode_address(request.address1)
    coords2 = mapbox_service.geocode_address(request.address2)
    
    if not coords1 or not coords2:
        raise HTTPException(status_code=400, detail="Could not geocode one or both addresses")
    
    lat1, lng1 = coords1
    lat2, lng2 = coords2
    
    # Calculate distance
    from geopy.distance import geodesic
    distance = geodesic((lat1, lng1), (lat2, lng2)).miles
    
    # Check if addresses are adjacent (proximity only)
    adjacent = mapbox_service.are_addresses_contiguously_adjacent(lat1, lng1, lat2, lng2)
    
    # Check if addresses are on same side of street
    same_side_of_street = mapbox_service.are_addresses_on_same_side_of_street(
        request.address1, request.address2
    )
    
    # Final adjacency requires both proximity AND same side of street
    final_adjacent = adjacent and same_side_of_street
    
    message = f"Distance: {distance:.4f} miles"
    if same_side_of_street:
        message += ", Same side of street"
    else:
        message += ", Different sides of street"
    
    return TestAdjacencyWithStreetResponse(
        adjacent=final_adjacent,
        same_side_of_street=same_side_of_street,
        distance_miles=distance,
        message=message
    )


@router.post("/test_adjacency_with_road_detection", response_model=TestAdjacencyWithRoadDetectionResponse)
async def test_adjacency_with_road_detection(request: TestAdjacencyWithRoadDetectionRequest):
    """
    Test if two addresses are adjacent with road-aware detection.
    This combines proximity check, side-of-street logic, AND road-crossing detection.
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
    
    # Check if addresses are adjacent (proximity only)
    adjacent = mapbox_service.are_addresses_contiguously_adjacent(lat1, lng1, lat2, lng2)
    
    # Check if addresses are on same side of street
    same_side_of_street = mapbox_service.are_addresses_on_same_side_of_street(
        request.address1, request.address2
    )
    
    # NEW: Check if accessible without crossing roads
    no_road_crossing = mapbox_service.is_accessible_without_crossing_road(
        (lat1, lng1), (lat2, lng2)
    )
    
    # Final adjacency requires proximity AND same side of street AND no road crossing
    final_adjacent = adjacent and same_side_of_street and no_road_crossing
    
    message = f"Distance: {distance:.4f} miles"
    if same_side_of_street:
        message += ", Same side of street"
    else:
        message += ", Different sides of street"
    
    if no_road_crossing:
        message += ", No road crossing"
    else:
        message += ", Road crossing detected"
    
    return TestAdjacencyWithRoadDetectionResponse(
        adjacent=final_adjacent,
        same_side_of_street=same_side_of_street,
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