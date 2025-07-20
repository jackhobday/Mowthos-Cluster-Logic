import requests
import logging
from typing import Optional, Tuple, Dict, Any
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

logger = logging.getLogger(__name__)

class MapboxService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.mapbox.com"
        # Fallback geocoder using OpenStreetMap
        self.fallback_geocoder = Nominatim(user_agent="mowthos_cluster_app")
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using Mapbox API with fallback to OpenStreetMap
        """
        # Try Mapbox first
        try:
            encoded_address = requests.utils.quote(address)
            url = f"{self.base_url}/geocoding/v5/mapbox.places/{encoded_address}.json"
            params = {
                'access_token': self.access_token,
                'types': 'address',
                'limit': 1
            }
            
            logger.info(f"Geocoding URL: {url}")
            logger.info(f"Params: {params}")
            
            response = requests.get(url, params=params)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features') and len(data['features']) > 0:
                    coords = data['features'][0]['center']
                    logger.info(f"Mapbox geocoding successful: {coords}")
                    return (coords[1], coords[0])  # lat, lng
                else:
                    logger.warning(f"Mapbox returned no results for: {address}")
            else:
                logger.warning(f"Mapbox API error: {response.text}")
                
        except Exception as e:
            logger.error(f"Mapbox geocoding failed: {e}")
        
        # Fallback to OpenStreetMap Nominatim
        try:
            logger.info(f"Trying OpenStreetMap fallback for: {address}")
            location = self.fallback_geocoder.geocode(address)
            if location:
                logger.info(f"OpenStreetMap geocoding successful: {location.latitude}, {location.longitude}")
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"OpenStreetMap also returned no results for: {address}")
        except Exception as e:
            logger.error(f"OpenStreetMap geocoding failed: {e}")
        
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
        Check if there's a road barrier between two points by determining if they're on the same side of the same street.
        Returns True if there's a road barrier (should NOT cluster), False if clear path.
        """
        try:
            # Method 1: Use Mapbox Tilequery API to get street information for both points
            # Query both addresses to get their street information
            
            # Query first address
            url1 = f"{self.base_url}/v4/mapbox.mapbox-streets-v8/tilequery/{lng1},{lat1}.json"
            params1 = {
                'access_token': self.access_token,
                'radius': 50,  # Increased radius to capture more road features
                'limit': 20
            }
            
            # Query second address
            url2 = f"{self.base_url}/v4/mapbox.mapbox-streets-v8/tilequery/{lng2},{lat2}.json"
            params2 = {
                'access_token': self.access_token,
                'radius': 50,  # Increased radius to capture more road features
                'limit': 20
            }
            
            logger.info(f"Checking street information for ({lat1}, {lng1}) and ({lat2}, {lng2})")
            
            response1 = requests.get(url1, params=params1)
            response2 = requests.get(url2, params=params2)
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                
                features1 = data1.get('features', [])
                features2 = data2.get('features', [])
                
                logger.info(f"Address 1 has {len(features1)} features, Address 2 has {len(features2)} features")
                
                # Extract street information from both addresses
                street1 = self._extract_street_info(features1)
                street2 = self._extract_street_info(features2)
                
                logger.info(f"Address 1 street: {street1}")
                logger.info(f"Address 2 street: {street2}")
                
                # If both addresses are on the same street, they should be adjacent
                if street1 and street2 and street1['name'] == street2['name']:
                    logger.info(f"Both addresses on same street: {street1['name']}")
                    return False  # No barrier - same street
                
                # If they're on different streets, check if there's a major road barrier
                if street1 and street2 and street1['name'] != street2['name']:
                    logger.info(f"Different streets: {street1['name']} vs {street2['name']}")
                    # Check if there's a major road between them
                    return self._check_major_road_barrier(lat1, lng1, lat2, lng2)
                
                # If we can't determine street info, be conservative and assume barrier
                # This prevents clustering addresses when we can't verify they're on the same street
                logger.warning("Could not determine street information, assuming barrier for safety")
                return True
            else:
                logger.warning(f"Tilequery API error: {response1.status_code}, {response2.status_code}")
                return self._check_road_barrier_directions(lat1, lng1, lat2, lng2)
                
        except Exception as e:
            logger.error(f"Error checking road barrier: {e}")
            return self._check_road_barrier_directions(lat1, lng1, lat2, lng2)

    def _extract_street_info(self, features):
        """Extract street information from Tilequery features."""
        for feature in features:
            properties = feature.get('properties', {})
            tilequery = properties.get('tilequery', {})
            layer = tilequery.get('layer', '')
            
            if layer == 'road':
                road_class = properties.get('class', '')
                road_name = properties.get('name', '')
                road_type = properties.get('type', '')
                
                # Consider more road types, but prioritize residential streets
                if road_name and road_class in ['residential', 'street', 'tertiary']:
                    return {
                        'name': road_name,
                        'class': road_class,
                        'distance': tilequery.get('distance', 0)
                    }
                # Also consider roads without class if they have a name
                elif road_name and road_type in ['street', 'residential']:
                    return {
                        'name': road_name,
                        'class': road_type,
                        'distance': tilequery.get('distance', 0)
                    }
        
        return None

    def _check_major_road_barrier(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """Check if there's a major road barrier between two points."""
        try:
            # Query midpoint for major roads
            mid_lat = (lat1 + lat2) / 2
            mid_lng = (lng1 + lng2) / 2
            
            url = f"{self.base_url}/v4/mapbox.mapbox-streets-v8/tilequery/{mid_lng},{mid_lat}.json"
            params = {
                'access_token': self.access_token,
                'radius': 15,
                'limit': 10
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                for feature in features:
                    properties = feature.get('properties', {})
                    tilequery = properties.get('tilequery', {})
                    layer = tilequery.get('layer', '')
                    distance = tilequery.get('distance', 0)
                    
                    if layer == 'road' and distance <= 10:
                        road_class = properties.get('class', '')
                        road_type = properties.get('type', '')
                        
                        # Major roads that are barriers
                        barrier_roads = ['primary', 'secondary', 'tertiary']
                        if road_class in barrier_roads:
                            logger.info(f"Major road barrier detected: {road_class} at {distance}m")
                            return True
                
                logger.info("No major road barrier detected")
                return False
            else:
                logger.warning(f"Tilequery API error: {response.status_code}")
                return True  # Assume barrier if we can't check
                
        except Exception as e:
            logger.error(f"Error checking major road barrier: {e}")
            return True  # Assume barrier if we can't check

    def _check_road_barrier_directions(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Fallback method using Mapbox Directions API to detect road barriers.
        """
        try:
            # Use Mapbox Directions API to get the actual route
            straight_distance = geodesic((lat1, lng1), (lat2, lng2)).meters
            
            url = f"{self.base_url}/directions/v5/mapbox/driving/{lng1},{lat1};{lng2},{lat2}.json"
            params = {
                'access_token': self.access_token,
                'geometries': 'geojson',
                'overview': 'full'
            }
            
            logger.info(f"Fallback: Using Directions API for road barrier check")
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get('routes', [])
                
                if routes:
                    route = routes[0]
                    route_distance = route.get('distance', 0)  # Distance in meters
                    
                    logger.info(f"Straight distance: {straight_distance:.1f}m, Route distance: {route_distance:.1f}m")
                    
                    # If route is significantly longer than straight distance, there's likely a barrier
                    if route_distance > straight_distance * 1.5:  # 50% longer
                        logger.info(f"Route significantly longer - likely road barrier")
                        return True
                    
                    # Check if route crosses major roads by analyzing waypoints
                    waypoints = route.get('geometry', {}).get('coordinates', [])
                    if len(waypoints) > 2:  # Route has detours
                        logger.info(f"Route has detours - likely road barrier")
                        return True
                    
                    logger.info("No significant road barriers detected via Directions API")
                    return False
                else:
                    logger.warning("No route found - assuming barrier")
                    return True
            else:
                logger.warning(f"Directions API error: {response.status_code}")
                # Final fallback: use distance-based heuristic
                return self._fallback_road_barrier_check(lat1, lng1, lat2, lng2)
                
        except Exception as e:
            logger.error(f"Error in Directions API fallback: {e}")
            # Final fallback: use distance-based heuristic
            return self._fallback_road_barrier_check(lat1, lng1, lat2, lng2)

    def _fallback_road_barrier_check(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Fallback method using coordinate analysis to detect likely road barriers.
        This is a simplified heuristic when Mapbox APIs are unavailable.
        """
        try:
            # Calculate the midpoint between the two addresses
            mid_lat = (lat1 + lat2) / 2
            mid_lng = (lng1 + lng2) / 2
            
            # Check if the midpoint is significantly different from both endpoints
            # This can indicate a road crossing
            distance1 = geodesic((lat1, lng1), (mid_lat, mid_lng)).meters
            distance2 = geodesic((lat2, lng2), (mid_lat, mid_lng)).meters
            total_distance = geodesic((lat1, lng1), (lat2, lng2)).meters
            
            # If the sum of distances to midpoint is significantly longer than direct distance,
            # there might be a road barrier
            if (distance1 + distance2) > total_distance * 1.2:
                logger.info("Fallback: Potential road barrier detected")
                return True
            
            # Additional check: if addresses are very close but on different streets,
            # they're likely separated by a road
            if total_distance < 100:  # Less than 100 meters
                # This is a simplified check - in practice you'd need street name data
                logger.info("Fallback: Very close addresses - checking for road separation")
                return False  # Assume no barrier for now
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fallback road barrier check: {e}")
            return False

    def are_addresses_contiguously_adjacent(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Enhanced adjacency check that considers both proximity AND road barriers.
        Returns True only if addresses are close AND no road barriers exist.
        """
        # First check proximity
        if not self.are_addresses_adjacent(lat1, lng1, lat2, lng2):
            logger.info("Addresses too far apart")
            return False
        
        # Then check for road barriers
        if self.check_road_barrier(lat1, lng1, lat2, lng2):
            logger.info("Road barrier detected - addresses not contiguously adjacent")
            return False
        
        logger.info("Addresses are contiguously adjacent")
        return True

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