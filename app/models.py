from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_host = Column(Boolean, default=False)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    cluster = relationship("Cluster", back_populates="users", foreign_keys=[cluster_id])
    hosted_clusters = relationship("Cluster", back_populates="host_user", foreign_keys="Cluster.host_user_id")
    lawn_boundaries = relationship("LawnBoundary", back_populates="user")


class Cluster(Base):
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    max_capacity = Column(Integer, default=5)  # Maximum 5 homes per cluster
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="cluster", foreign_keys="User.cluster_id")
    host_user = relationship("User", back_populates="hosted_clusters", foreign_keys=[host_user_id])


class LawnBoundary(Base):
    __tablename__ = "lawn_boundaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    boundary_coordinates = Column(Text, nullable=False)  # JSON string of polygon coordinates
    area_sqm = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="lawn_boundaries") 