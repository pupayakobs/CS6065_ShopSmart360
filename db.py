import os
import urllib
from sqlalchemy import create_engine

def get_engine():
    server = os.environ.get("DB_SERVER", "shopsmart360.database.windows.net")
    database = os.environ.get("DB_NAME", "sql-shopsmart360")
    username = os.environ.get("DB_USER", "shopsmart360admin")
    password = os.environ.get("DB_PASS", "")

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=120;"
    )
    params = urllib.parse.quote_plus(conn_str)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

