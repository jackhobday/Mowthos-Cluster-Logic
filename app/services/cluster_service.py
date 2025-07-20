from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple
from geopy.distance import geodesic
import json

from app.models import User, Cluster, LawnBoundary
from app.schemas import HostRegistrationRequest, JoinClusterRequest, ClusterAssignmentResponse
from app.services.mapbox_service import MapboxService
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ClusterService:
    def __init__(self):
        self.max_cluster_capacity = 5
        self.min_cluster_capacity = 3
        self.mapbox_service = MapboxService(settings.mapbox_access_token)
    
    def register_host_home(self, db: Session, request: HostRegistrationRequest) -> ClusterAssignmentResponse:
        """
        Register a new host home and create a new cluster.
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == request.email).first()
            if existing_user:
                return ClusterAssignmentResponse(
                    success=False,
                    message="User with this email already exists"
                )
            
            # Create new user as host
            new_user = User(
                email=request.email,
                name=request.name,
                latitude=request.latitude,
                longitude=request.longitude,
                is_host=True
            )
            db.add(new_user)
            db.flush()  # Get the user ID
            
            # Create new cluster
            new_cluster = Cluster(
                name=request.cluster_name,
                host_user_id=new_user.id,
                max_capacity=self.max_cluster_capacity
            )
            db.add(new_cluster)
            db.flush()  # Get the cluster ID
            
            # Assign user to cluster
            new_user.cluster_id = new_cluster.id
            
            # Create lawn boundary for the host
            boundary_info = self.mapbox_service.get_property_boundaries(
                request.latitude, request.longitude
            )
            if boundary_info:
                lawn_boundary = LawnBoundary(
                    user_id=new_user.id,
                    boundary_coordinates=json.dumps(boundary_info),
                    area_sqm=100.0  # Default area if we can't calculate it
                )
                db.add(lawn_boundary)
            
            db.commit()
            
            return ClusterAssignmentResponse(
                success=True,
                message=f"Successfully registered as host and created cluster '{request.cluster_name}'",
                cluster_id=new_cluster.id,
                assigned_host=new_user
            )
            
        except Exception as e:
            db.rollback()
            return ClusterAssignmentResponse(
                success=False,
                message=f"Error registering host: {str(e)}"
            )
    
    def join_cluster(self, db: Session, request: JoinClusterRequest) -> ClusterAssignmentResponse:
        """
        Assign a non-host user to the closest eligible cluster with valid adjacency.
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == request.email).first()
            if existing_user:
                return ClusterAssignmentResponse(
                    success=False,
                    message="User with this email already exists"
                )
            
            # Find eligible clusters (not at max capacity)
            # Get all clusters and check their current member count
            all_clusters = db.query(Cluster).all()
            eligible_clusters = []
            
            for cluster in all_clusters:
                # Count users in this cluster
                user_count = db.query(User).filter(User.cluster_id == cluster.id).count()
                if user_count < cluster.max_capacity:
                    eligible_clusters.append(cluster)
            
            if not eligible_clusters:
                return ClusterAssignmentResponse(
                    success=False,
                    message="No eligible clusters available. All clusters are at maximum capacity."
                )
            
            # Find the closest cluster with valid adjacency
            best_cluster = None
            best_distance = float('inf')
            
            for cluster in eligible_clusters:
                # Get host user for this cluster
                host_user = db.query(User).filter(User.id == cluster.host_user_id).first()
                if not host_user:
                    continue
                
                # Check if user can be assigned to this cluster
                can_assign = self._can_assign_to_cluster(
                    db, request.latitude, request.longitude, cluster.id
                )
                
                if can_assign:
                    distance = geodesic(
                        (request.latitude, request.longitude),
                        (host_user.latitude, host_user.longitude)
                    ).meters
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_cluster = cluster
            
            if not best_cluster:
                return ClusterAssignmentResponse(
                    success=False,
                    message="No eligible clusters found with adjacent lawn boundaries. Consider registering as a host."
                )
            
            # Create new user
            new_user = User(
                email=request.email,
                name=request.name,
                latitude=request.latitude,
                longitude=request.longitude,
                is_host=False,
                cluster_id=best_cluster.id
            )
            db.add(new_user)
            db.flush()
            
            # Create lawn boundary for the new user
            boundary_info = self.mapbox_service.get_property_boundaries(
                request.latitude, request.longitude
            )
            if boundary_info:
                lawn_boundary = LawnBoundary(
                    user_id=new_user.id,
                    boundary_coordinates=json.dumps(boundary_info),
                    area_sqm=100.0  # Default area if we can't calculate it
                )
                db.add(lawn_boundary)
            
            db.commit()
            
            # Get host user for response
            host_user = db.query(User).filter(User.id == best_cluster.host_user_id).first()
            
            return ClusterAssignmentResponse(
                success=True,
                message=f"Successfully joined cluster '{best_cluster.name}'",
                cluster_id=best_cluster.id,
                assigned_host=host_user
            )
            
        except Exception as e:
            db.rollback()
            return ClusterAssignmentResponse(
                success=False,
                message=f"Error joining cluster: {str(e)}"
            )
    
    def _can_assign_to_cluster(self, db: Session, lat: float, lon: float, cluster_id: int) -> bool:
        """
        Check if a user can be assigned to a specific cluster based on contiguous adjacency rules.
        """
        # Get all users in the cluster
        cluster_users = db.query(User).filter(User.cluster_id == cluster_id).all()
        
        if not cluster_users:
            return False
        
        # Check if the new user is contiguously adjacent to at least one existing user in the cluster
        for user in cluster_users:
            if self.mapbox_service.are_addresses_contiguously_adjacent(lat, lon, user.latitude, user.longitude):
                return True
        
        return False
    
    def get_cluster_info(self, db: Session, cluster_id: int) -> Optional[Cluster]:
        """Get cluster information by ID"""
        return db.query(Cluster).filter(Cluster.id == cluster_id).first()
    
    def get_all_clusters(self, db: Session) -> List[Cluster]:
        """Get all clusters"""
        return db.query(Cluster).all()

# Global instance
cluster_service = ClusterService() 