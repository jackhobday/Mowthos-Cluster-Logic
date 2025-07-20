from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from geopy.distance import geodesic


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    is_host: bool
    cluster_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ClusterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    max_capacity: int = Field(..., ge=3, le=5)


class ClusterCreate(ClusterBase):
    host_user_id: int


class ClusterResponse(ClusterBase):
    id: int
    host_user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    users: List[UserResponse] = []
    
    class Config:
        from_attributes = True


class LawnBoundaryBase(BaseModel):
    boundary_coordinates: str  # JSON string of polygon coordinates
    area_sqm: Optional[float] = Field(None, ge=0)


class LawnBoundaryCreate(LawnBoundaryBase):
    user_id: int


class LawnBoundaryResponse(LawnBoundaryBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class HostRegistrationRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    cluster_name: str = Field(..., min_length=1, max_length=100)


class JoinClusterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ClusterAssignmentResponse(BaseModel):
    success: bool
    message: str
    cluster_id: Optional[int] = None
    assigned_host: Optional[UserResponse] = None


class MowerStatusResponse(BaseModel):
    cluster_id: int
    status: str  # "idle", "mowing", "charging", "error"
    current_location: Optional[Dict[str, float]] = None
    battery_level: Optional[float] = None
    last_updated: datetime 