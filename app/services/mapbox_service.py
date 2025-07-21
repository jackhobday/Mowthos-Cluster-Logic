import os
import requests
import logging
from typing import Tuple, Optional, List, Dict, Any
from geopy.distance import geodesic
import re

# Add new imports for road-aware detection
try:
    import osmnx as ox
    import shapely
    from shapely.geometry import LineString, Point
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    logging.warning("OSMnx not available. Road-aware detection will be disabled.")

logger = logging.getLogger(__name__)

class MapboxService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com"
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using Mapbox Geocoding API.
        Returns (latitude, longitude) or None if not found.
        """
        try:
            url = f"{self.base_url}/geocoding/v5/mapbox.places/{address}.json"
            params = {
                "access_token": self.access_token,
                "limit": 1,
                "types": "address"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data["features"]:
                coords = data["features"][0]["center"]
                return coords[1], coords[0]  # Return (lat, lng)
            
            return None
            
        except Exception as e:
            logger.error(f"Geocoding error for {address}: {e}")
            return None

    def are_addresses_adjacent(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Check if two addresses are adjacent (within 0.05 miles = ~80 meters)
        This allows for slightly larger clusters while still being restrictive
        """
        distance = geodesic((lat1, lng1), (lat2, lng2)).miles
        logger.info(f"Distance between addresses: {distance:.4f} miles")
        return distance <= 0.05  # Increased threshold for larger clusters

    def check_road_barrier(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Check if there's a road barrier between two points.
        
        REMOVED: TileQuery road detection logic since odd/even side-of-street logic 
        provides sufficient filtering without additional API calls.
        
        Returns False (no barrier) to allow clustering based on proximity and side-of-street logic only.
        """
        # Road barrier detection removed - using odd/even side-of-street logic instead
        return False  # No road barrier detected

    def are_addresses_contiguously_adjacent(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Enhanced adjacency check that considers proximity only.
        Road barrier detection removed - using odd/even side-of-street logic instead.
        Returns True only if addresses are close enough.
        """
        # Check proximity only - road barriers handled by side-of-street logic
        if not self.are_addresses_adjacent(lat1, lng1, lat2, lng2):
            logger.info("Addresses too far apart")
            return False
        
        logger.info("Addresses are adjacent (proximity check passed)")
        return True

    def are_addresses_on_same_side_of_street(self, address1: str, address2: str) -> bool:
        """
        Check if two addresses are on the same side of the street using odd/even parity.
        Returns True if both addresses have the same parity (both odd or both even).
        """
        host_number = self._extract_house_number(address1)
        neighbor_number = self._extract_house_number(address2)
        
        if host_number is None or neighbor_number is None:
            return False
        
        # Check if both numbers have the same parity (both odd or both even)
        host_parity = host_number % 2
        neighbor_parity = neighbor_number % 2
        
        return host_parity == neighbor_parity
    
    def _extract_house_number(self, address: str) -> Optional[int]:
        """Extract house number from address string."""
        parts = address.split()
        if parts and parts[0].isdigit():
            return int(parts[0])
        return None
    
    def is_accessible_without_crossing_road(self, host_coords: Tuple[float, float], 
                                          candidate_coords: Tuple[float, float]) -> bool:
        """
        Road-aware neighbor detection: Check if candidate home can be connected to host home
        without crossing a drivable road.
        
        Args:
            host_coords: (lat, lon) tuple for the host home
            candidate_coords: (lat, lon) tuple for the neighbor candidate
            
        Returns:
            True if no road is crossed; False otherwise
        """
        if not OSMNX_AVAILABLE:
            logger.warning("OSMnx not available. Skipping road-crossing check.")
            return True  # Default to allowing if OSMnx unavailable
        
        try:
            import time
            start_time = time.time()
            
            logger.info(f"Starting road detection: Host {host_coords} -> Candidate {candidate_coords}")
            
            # Download road network near the host home (100m radius) with timeout
            G = ox.graph_from_point(host_coords, dist=100, network_type='drive')
            edges = ox.graph_to_gdfs(G, nodes=False)
            
            logger.info(f"Found {len(edges)} road segments in area")
            
            if edges.empty:
                logger.info("No roads found in area. Allowing connection.")
                return True
            
            # Buffer the road geometry (~5m width for typical residential roads)
            edges['geometry'] = edges['geometry'].buffer(0.00005)  # ~5 meters
            
            # Create line from host to candidate (convert to (lon, lat) for Shapely)
            line = LineString([
                (host_coords[1], host_coords[0]),  # (lon, lat)
                (candidate_coords[1], candidate_coords[0])  # (lon, lat)
            ])
            
            logger.info(f"Testing line: {line.coords[:]}")
            
            # Check intersection with any road segment
            intersection_count = 0
            for i, geom in enumerate(edges['geometry']):
                if line.intersects(geom):
                    logger.info(f"Road intersection detected with road segment {i}. Rejecting candidate.")
                    intersection_count += 1
                    return False
            
            elapsed_time = time.time() - start_time
            logger.info(f"No road intersection detected. Allowing connection. (Took {elapsed_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error in road-crossing check: {e}")
            return True  # Default to allowing if error occurs

    def get_property_boundaries(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """
        Get property boundaries for a given location
        """
        try:
            url = f"{self.base_url}/geocoding/v5/mapbox.places/{lng},{lat}.json"
            params = {
                'access_token': self.access_token,
                'types': 'address'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features') and len(data['features']) > 0:
                    feature = data['features'][0]
                    return {
                        'bbox': feature.get('bbox'),
                        'center': feature.get('center'),
                        'place_name': feature.get('place_name'),
                        'properties': feature.get('properties', {})
                    }
            else:
                logger.error(f"Error getting property boundaries: {response.status_code} {response.reason}")
                
        except Exception as e:
            logger.error(f"Error getting property boundaries: {e}")
        
        return None 