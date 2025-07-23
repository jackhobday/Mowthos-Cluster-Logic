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
            return False  # Default to allowing if OSMnx unavailable
        
        try:
            import time
            import matplotlib.pyplot as plt
            from shapely.geometry import LineString, Point
            start_time = time.time()
            
            logger.info(f"Starting road detection: Host {host_coords} -> Candidate {candidate_coords}")
            
            # Download road network near the host home (300m radius) with timeout
            G = ox.graph_from_point(host_coords, dist=300, network_type='drive')
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
            
            # Plotting for debug
            fig, ax = plt.subplots(figsize=(8, 8))
            # Plot all road segments
            for geom in edges['geometry']:
                try:
                    x, y = geom.exterior.xy
                    ax.plot(x, y, color='gray', alpha=0.5)
                except Exception:
                    # Some geometries may not have exterior (e.g., MultiPolygon)
                    pass
            # Plot the line between homes
            x, y = line.xy
            ax.plot(x, y, color='blue', linewidth=2, label='Home-to-Home Line')
            # Plot the two homes
            ax.scatter([host_coords[1], candidate_coords[1]], [host_coords[0], candidate_coords[0]], color='red', s=100, zorder=5, label='Homes')
            # Check intersection with any road segment
            intersection_found = False
            for i, geom in enumerate(edges['geometry']):
                if line.intersects(geom):
                    intersection = line.intersection(geom)
                    if intersection.is_empty:
                        continue
                    intersection_found = True
                    # Plot intersection point(s)
                    if intersection.geom_type == 'Point':
                        ax.plot(intersection.x, intersection.y, 'go', markersize=12, label='Intersection' if i == 0 else None)
                    elif intersection.geom_type == 'MultiPoint':
                        for pt in intersection.geoms:
                            ax.plot(pt.x, pt.y, 'go', markersize=12, label='Intersection' if i == 0 else None)
                    elif intersection.geom_type == 'LineString':
                        x, y = intersection.xy
                        ax.plot(x, y, 'g--', linewidth=3, label='Intersection Line' if i == 0 else None)
                    elif intersection.geom_type == 'MultiLineString':
                        for linestr in intersection.geoms:
                            x, y = linestr.xy
                            ax.plot(x, y, 'g--', linewidth=3, label='Intersection Line' if i == 0 else None)
                    elif intersection.geom_type == 'GeometryCollection':
                        for geom_part in intersection.geoms:
                            if geom_part.geom_type == 'Point':
                                ax.plot(geom_part.x, geom_part.y, 'go', markersize=12, label='Intersection' if i == 0 else None)
                            elif geom_part.geom_type == 'LineString':
                                x, y = geom_part.xy
                                ax.plot(x, y, 'g--', linewidth=3, label='Intersection Line' if i == 0 else None)
            ax.legend()
            ax.set_title('Road Detection Debug')
            plt.xlabel('Longitude')
            plt.ylabel('Latitude')
            plt.savefig('debug_road_detection.png')
            plt.close(fig)
            # End plotting
            if intersection_found:
                logger.info("Road intersection detected. Rejecting candidate.")
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