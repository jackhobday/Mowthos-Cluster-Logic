# Mowthos Cluster Logic

A FastAPI-based microservice that manages neighborhood clusters for robotic mowing operations. The service groups users into clusters centered around host homes, ensuring physically adjacent lawns for efficient mowing operations.

## Features

- **Host Registration**: Designate users as hosts to create new clusters
- **Cluster Assignment**: Automatically assign non-host users to the closest eligible cluster
- **Adjacency Validation**: Ensure clusters consist of physically adjacent lawns
- **Mapbox Integration**: Use geospatial APIs to determine property boundaries and adjacency
- **PyMammation Ready**: Stub endpoints for future robotic mowing integration

## Cluster Rules

- A host home can serve 3–5 nearby homes
- Clusters must consist of **physically adjacent lawns** — homes must share lawn boundaries with no roads between them
- When a user signs up as a host, they create a new cluster
- When a user signs up as a non-host, they're assigned to the closest eligible cluster with valid adjacency

## API Endpoints

### Host Registration
```
POST /clusters/register_host_home
```
Register a new host home and create a new cluster.

**Request Body:**
```json
{
  "email": "host@example.com",
  "name": "John Doe",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "cluster_name": "Sunset Neighborhood"
}
```

### Join Cluster
```
POST /clusters/join_cluster
```
Assign a non-host user to the closest eligible cluster with valid adjacency.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "Jane Smith",
  "latitude": 37.7750,
  "longitude": -122.4195
}
```

### Get All Clusters
```
GET /clusters/
```
Retrieve all clusters with their users.

### Get Cluster Details
```
GET /clusters/{cluster_id}
```
Get detailed information about a specific cluster.

### Mower Status (Stub)
```
GET /clusters/{cluster_id}/mower
```
Get mower status for a cluster (stub endpoint for PyMammation integration).

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the example environment file and configure your settings:
```bash
cp env.example .env
```

Edit `.env` with your configuration:
```env
# Mapbox API Configuration
MAPBOX_ACCESS_TOKEN=your_mapbox_access_token_here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/mowthos_cluster

# Application Settings
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 3. Database Setup
The application uses SQLAlchemy with PostgreSQL. Make sure you have:
- PostgreSQL installed and running
- A database created for the application
- The correct DATABASE_URL in your `.env` file

### 4. Run the Application
```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## Architecture

### Models
- **User**: Represents users with location and host status
- **Cluster**: Represents a group of adjacent homes with a host
- **LawnBoundary**: Stores property boundary coordinates and area

### Services
- **ClusterService**: Handles cluster management and user assignment logic
- **MapboxService**: Integrates with Mapbox API for geospatial operations

### Key Features
- **Adjacency Checking**: Uses Mapbox Directions API to determine if properties are separated by roads
- **Distance Calculation**: Uses geodesic distance for accurate geographic calculations
- **Boundary Analysis**: Fetches and stores property boundaries for lawn area calculations

## Development

### Project Structure
```
Mowthos-Cluster-Logic/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── clusters.py      # Cluster API routes
│   └── services/
│       ├── __init__.py
│       ├── cluster_service.py    # Cluster business logic
│       └── mapbox_service.py    # Mapbox integration
├── requirements.txt
├── run.py                   # Application runner
├── env.example              # Environment template
└── README.md
```

### Testing
The application includes comprehensive error handling and validation:
- Input validation using Pydantic schemas
- Database transaction management
- Graceful fallbacks for Mapbox API failures
- Detailed error messages for debugging

### Future Enhancements
- **PyMammation Integration**: Connect to the robotic mowing library
- **Real-time Updates**: WebSocket support for live mower status
- **Advanced GIS**: Enhanced geospatial analysis with PostGIS
- **Authentication**: User authentication and authorization
- **Monitoring**: Health checks and metrics collection

## License

This project is licensed under the MIT License - see the LICENSE file for details.
