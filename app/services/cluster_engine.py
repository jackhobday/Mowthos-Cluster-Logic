import csv
import time
import numpy as np
from typing import List
from sklearn.neighbors import BallTree
from app.services.mapbox_service import MapboxService
from app.config import settings
import os

# Path to the address CSV (all possible homes)
ADDRESS_CSV = 'olmsted_addresses_559xx.csv'
# Path to the registered host homes CSV
HOST_HOMES_CSV = 'host_homes.csv'

# Haversine radius for 80 meters (in radians)
EARTH_RADIUS_M = 6371000
RADIUS_METERS = 80
RADIUS_RADIANS = RADIUS_METERS / EARTH_RADIUS_M

mapbox_service = MapboxService(settings.mapbox_access_token)

def ensure_host_homes_csv():
    """Create a template host_homes.csv if it doesn't exist."""
    if not os.path.exists(HOST_HOMES_CSV):
        with open(HOST_HOMES_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'city', 'state', 'latitude', 'longitude'])
            writer.writeheader()
            # Example row
            writer.writerow({
                'address': '123 Main St',
                'city': 'Rochester',
                'state': 'MN',
                'latitude': 44.0123,
                'longitude': -92.1234
            })

def load_addresses_from_csv(path: str) -> List[dict]:
    """Load addresses from a CSV file, returning a list of dicts with full address and lat/lon."""
    addresses = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Compose full address
            full_address = f"{row['address']}, {row['city']}, {row['state']}"
            addresses.append({
                'full_address': full_address,
                'address': row['address'],
                'city': row['city'],
                'state': row['state'],
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude'])
            })
    return addresses

def discover_neighbors_for_host(host_address: str) -> List[str]:
    """
    Find all qualified neighbors for a host home using road-aware detection.
    Only considers registered host homes as the host.
    Returns a list of qualified neighbor full addresses (street, city, state).
    """
    ensure_host_homes_csv()
    # Geocode the host address
    host_coords = mapbox_service.geocode_address(host_address)
    if not host_coords:
        print(f"[ERROR] Could not geocode host address: {host_address}")
        return []
    # Load all candidate addresses (from the big CSV)
    candidates = load_addresses_from_csv(ADDRESS_CSV)
    # Load the host home full address (from host_homes.csv)
    host_homes = load_addresses_from_csv(HOST_HOMES_CSV)
    # Find the host home entry that matches the input address
    host_home = None
    for h in host_homes:
        if host_address.lower() in h['full_address'].lower():
            host_home = h
            break
    if not host_home:
        print(f"[ERROR] Host home not found in host_homes.csv: {host_address}")
        return []
    # Build BallTree for all candidates
    candidate_coords = np.array([[c['latitude'], c['longitude']] for c in candidates])
    candidate_coords_rad = np.radians(candidate_coords)
    tree = BallTree(candidate_coords_rad, metric='haversine')
    host_latlon_rad = np.radians([[host_home['latitude'], host_home['longitude']]])
    idxs = tree.query_radius(host_latlon_rad, r=RADIUS_RADIANS)[0]
    qualified_neighbors = []
    start = time.time()
    for idx in idxs:
        candidate = candidates[idx]
        if candidate['full_address'].lower() == host_home['full_address'].lower():
            continue  # skip self
        # Road-aware check
        if mapbox_service.is_accessible_without_crossing_road(
            (host_home['latitude'], host_home['longitude']),
            (candidate['latitude'], candidate['longitude'])
        ):
            qualified_neighbors.append(candidate['full_address'])
    elapsed = time.time() - start
    print(f"[DEBUG] Checked {len(idxs)} candidates, found {len(qualified_neighbors)} qualified neighbors. Avg time: {elapsed/max(1,len(idxs)):.2f}s per neighbor.")
    return qualified_neighbors

def find_qualified_host_for_neighbor(neighbor_address: str) -> List[str]:
    """
    For a given neighbor address, find all registered host homes for which this address qualifies as a neighbor.
    Returns a list of host home full addresses (street, city, state).
    """
    ensure_host_homes_csv()
    # Geocode neighbor address
    neighbor_coords = mapbox_service.geocode_address(neighbor_address)
    if not neighbor_coords:
        print(f"[ERROR] Could not geocode neighbor address: {neighbor_address}")
        return []
    # Load all host homes
    host_homes = load_addresses_from_csv(HOST_HOMES_CSV)
    # Build BallTree for all host homes
    host_coords = np.array([[h['latitude'], h['longitude']] for h in host_homes])
    host_coords_rad = np.radians(host_coords)
    tree = BallTree(host_coords_rad, metric='haversine')
    neighbor_latlon_rad = np.radians([[neighbor_coords[0], neighbor_coords[1]]])
    idxs = tree.query_radius(neighbor_latlon_rad, r=RADIUS_RADIANS)[0]
    qualified_hosts = []
    start = time.time()
    for idx in idxs:
        host = host_homes[idx]
        # Road-aware check
        if mapbox_service.is_accessible_without_crossing_road(
            (host['latitude'], host['longitude']),
            (neighbor_coords[0], neighbor_coords[1])
        ):
            qualified_hosts.append(host['full_address'])
    elapsed = time.time() - start
    print(f"[DEBUG] Checked {len(idxs)} hosts, found {len(qualified_hosts)} qualified hosts. Avg time: {elapsed/max(1,len(idxs)):.2f}s per host.")
    return qualified_hosts 