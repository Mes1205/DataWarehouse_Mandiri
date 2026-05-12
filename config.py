from sqlalchemy import create_engine

DB_URL = "DB_URL"

def get_engine():
    return create_engine(DB_URL)