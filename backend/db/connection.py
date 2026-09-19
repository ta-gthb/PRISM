import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """
    Return a new psycopg2 connection using the DATABASE_URL env variable.
    Rows are returned as RealDict objects so they serialise cleanly to JSON.
    Callers are responsible for closing the connection.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it to your .env file or deployment environment."
        )
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
