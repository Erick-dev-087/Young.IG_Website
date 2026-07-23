from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "development"
    app_port: int = 8000
    app_secret: str = "your-secret-key-here"

    # Database
    db_port: int = 5435
    db_name: str = "young_auto_db"
    db_user: str = "young_auto_user"
    db_password: str = "your-database-password-here"
    database_url: str = "postgresql://neondb_owner:npg_ajvtzL2sZ8SB@ep-lively-dawn-as5k4wbw-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800
    db_echo: bool = False
    
    # JWT Authentication
    jwt_secret: str = "your-jwt-secret-here"
    jwt_expiry: str = "3600"
    jwt_refresh_secret: str = "your-jwt-refresh-secret-here"
    jwt_refresh_expiry: str = "2592000"
    jwt_algorithm: str = "HS256"

    password_reset: str = "your-password-reset-secret-here"
    password_reset_expiry: str = "3600"

    # Cloudinary (image storage)
    cloudinary_cloud_name: str = "your-cloud-name"
    cloudinary_api_key: str = "your-api-key"
    cloudinary_api_secret: str = "your-api-secret"
    cloudinary_folder: str = "young_ig_inspections"

    
    def get_async_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
        # asyncpg does not support sslmode or channel_binding kwargs from the URL
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("?channel_binding=require&", "?")
        url = url.replace("&channel_binding=require", "")
        url = url.replace("?channel_binding=require", "")
        
        return url


settings = Settings()
    