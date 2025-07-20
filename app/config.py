from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Mapbox API Configuration
    mapbox_access_token: str
    
    # Database Configuration
    database_url: str = "sqlite:///./mowthos_cluster.db"
    
    # Application Settings
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() 