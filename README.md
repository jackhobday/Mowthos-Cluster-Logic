# Mowthos Cluster Logic Backend

## API Endpoints

All endpoints are under the `/clusters` prefix.

### 1. Register Host Home
- **POST** `/clusters/register_host_home_csv`
- **Purpose:** Register a new host home (adds to host_homes.csv)
- **Request:**
```
{
  "address": "123 Main St",
  "city": "Rochester",
  "state": "MN",
  "latitude": 44.0123,   // optional
  "longitude": -92.1234  // optional
}
```
- **Response:**
```
{
  "success": true,
  "full_address": "123 Main St, Rochester, MN",
  "latitude": 44.0123,
  "longitude": -92.1234
}
```

### 2. Register Neighbor Home
- **POST** `/clusters/register_neighbor_home_csv`
- **Purpose:** Register a new neighbor home (adds to neighbor_homes.csv)
- **Request:**
```
{
  "address": "456 Elm St",
  "city": "Rochester",
  "state": "MN",
  "latitude": 44.0124,   // optional
  "longitude": -92.1235  // optional
}
```
- **Response:**
```
{
  "success": true,
  "full_address": "456 Elm St, Rochester, MN",
  "latitude": 44.0124,
  "longitude": -92.1235
}
```

### 3. Discover Qualified Neighbors for Host Home
- **POST** `/clusters/discover_neighbors_for_host_csv`
- **Purpose:** Given a host home, return all qualified neighbors (road-aware)
- **Request:**
```
{
  "address": "123 Main St",
  "city": "Rochester",
  "state": "MN"
}
```
- **Response:**
```
{
  "qualified_addresses": [
    "456 Elm St, Rochester, MN",
    "789 Oak Ave, Rochester, MN"
  ]
}
```

### 4. Find Qualified Hosts for Neighbor Home
- **POST** `/clusters/find_qualified_host_for_neighbor_csv`
- **Purpose:** Given a neighbor home, return all host homes for which it qualifies
- **Request:**
```
{
  "address": "456 Elm St",
  "city": "Rochester",
  "state": "MN"
}
```
- **Response:**
```
{
  "qualified_addresses": [
    "123 Main St, Rochester, MN"
  ]
}
```

### 5. Geocode Address
- **POST** `/clusters/geocode`
- **Purpose:** Geocode an address to get latitude/longitude
- **Request:**
```
{
  "address": "123 Main St, Rochester, MN"
}
```
- **Response:**
```
{
  "latitude": 44.0123,
  "longitude": -92.1234,
  "address": "123 Main St, Rochester, MN"
}
```

---

## CSV Format

### host_homes.csv & neighbor_homes.csv
- **Columns:**
  - `address` (string, required)
  - `city` (string, required)
  - `state` (string, required)
  - `latitude` (float, required)
  - `longitude` (float, required)
- **Example row:**
```
123 Main St,Rochester,MN,44.0123,-92.1234
```

---

## Deprecated/Legacy Endpoints
- All database-based cluster logic and endpoints are deprecated and not used in the CSV-based flow.
- Only the endpoints listed above are supported and maintained.

---

## Notes
- All address-based queries use full address (street, city, state).
- Road-aware adjacency is used for all neighbor/host qualification.
- The backend is ready for frontend integration and further extension.
