from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
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
from app.services.cluster_engine import (
    register_host_home as register_host_home_csv,
    register_neighbor_home as register_neighbor_home_csv,
    discover_neighbors_for_host,
    find_qualified_host_for_neighbor
)

router = APIRouter(prefix="/clusters", tags=["clusters"])

# Create MapboxService instance
mapbox_service = MapboxService(settings.mapbox_access_token)


class GeocodeRequest(BaseModel):
    address: str


class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    address: str


class RegisterHostHomeCSVRequest(BaseModel):
    address: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RegisterNeighborHomeCSVRequest(BaseModel):
    address: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RegisterHomeCSVResponse(BaseModel):
    success: bool
    full_address: str = None
    latitude: float = None
    longitude: float = None
    message: str = None


class AddressRequest(BaseModel):
    address: str
    city: str
    state: str

class QualifiedAddressesResponse(BaseModel):
    qualified_addresses: list[str]


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


# Remove or comment out all endpoints and code related to DB-based cluster logic (register_host_home, join_cluster, get_all_clusters, get_cluster, get_mower_status, and related imports/models)


@router.post("/register_host_home_csv", response_model=RegisterHomeCSVResponse)
async def register_host_home_csv_endpoint(request: RegisterHostHomeCSVRequest):
    result = register_host_home_csv(request.address, request.city, request.state, request.latitude, request.longitude)
    return RegisterHomeCSVResponse(**result)

@router.post("/register_neighbor_home_csv", response_model=RegisterHomeCSVResponse)
async def register_neighbor_home_csv_endpoint(request: RegisterNeighborHomeCSVRequest):
    result = register_neighbor_home_csv(request.address, request.city, request.state, request.latitude, request.longitude)
    return RegisterHomeCSVResponse(**result)

@router.post("/discover_neighbors_for_host_csv", response_model=QualifiedAddressesResponse)
async def discover_neighbors_for_host_csv_endpoint(request: AddressRequest):
    full_address = f"{request.address}, {request.city}, {request.state}"
    neighbors = discover_neighbors_for_host(full_address)
    return QualifiedAddressesResponse(qualified_addresses=neighbors)

@router.post("/find_qualified_host_for_neighbor_csv", response_model=QualifiedAddressesResponse)
async def find_qualified_host_for_neighbor_csv_endpoint(request: AddressRequest):
    full_address = f"{request.address}, {request.city}, {request.state}"
    hosts = find_qualified_host_for_neighbor(full_address)
    return QualifiedAddressesResponse(qualified_addresses=hosts) 