"""
Configuration module for Data Lake Loader
"""
from pathlib import Path
from typing import Literal


class Config:
    """Application configuration"""

    DATA_ROOT_FOLDER = Path(r"D:\DataRootFolder")
    INVALID_FILES_FOLDER = DATA_ROOT_FOLDER / "_InvalidFiles"

    DB_TYPE: Literal["sqlserver", "postgres"] = "sqlserver"
    DB_HOST = "localhost"
    DB_NAME = "ORBIT_DL"
    DB_USER = None
    DB_PASSWORD = None

    FIELD_TYPE = "NVARCHAR(MAX)"

    IMPORTED_FOLDER_NAME = "Imported"
    ERROR_FOLDER_NAME = "Error"

    @classmethod
    def get_connection_string(cls) -> str:
        """Get database connection string based on DB type"""
        if cls.DB_TYPE == "sqlserver":
            driver = "{ODBC Driver 17 for SQL Server}"
            conn_str = (
                f"DRIVER={driver};"
                f"SERVER={cls.DB_HOST};"
                f"DATABASE={cls.DB_NAME};"
                f"Trusted_Connection=yes;"
            )
            if cls.DB_USER:
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={cls.DB_HOST};"
                    f"DATABASE={cls.DB_NAME};"
                    f"UID={cls.DB_USER};"
                    f"PWD={cls.DB_PASSWORD};"
                )
            return conn_str
        elif cls.DB_TYPE == "postgres":
            user_part = f"{cls.DB_USER}:{cls.DB_PASSWORD}@" if cls.DB_USER else ""
            return f"postgresql://{user_part}{cls.DB_HOST}/{cls.DB_NAME}"
        else:
            raise ValueError(f"Unsupported database type: {cls.DB_TYPE}")
