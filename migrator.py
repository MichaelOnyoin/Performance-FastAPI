import argparse
import os
import sys
from sqlalchemy import create_engine, inspect, MetaData, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Import your SQLAlchemy Base and models so table schemas are registered
from app import models
from app.database import Base

# 1. Setup Engines
SQLITE_URL = "sqlite:///./data/performance.db"
POSTGRES_URL = os.environ.get("DB_URL")

if not POSTGRES_URL:
    print("Error: DB_URL environment variable is not set.")
    sys.exit(1)

if POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql://", 1)

sqlite_engine = create_engine(SQLITE_URL)
postgres_engine = create_engine(POSTGRES_URL)

# 2. Reflect SQLite Schema
sqlite_meta = MetaData()
sqlite_meta.reflect(bind=sqlite_engine)

# Default migration order respecting Foreign Key constraints
DEFAULT_TABLES = ["users", "employees", "kpis", "entries", "employee_kpis"]


def ensure_table_exists(table_name: str):
    """Creates the specific table in Neon Postgres if it does not exist."""
    pg_inspector = inspect(postgres_engine)
    if pg_inspector.has_table(table_name):
        return

    if table_name in Base.metadata.tables:
        print(f"Table '{table_name}' not found in Neon. Creating it from models...")
        Base.metadata.tables[table_name].create(bind=postgres_engine)
    elif table_name in sqlite_meta.tables:
        print(f"Table '{table_name}' not found in Neon. Creating it from SQLite reflection...")
        sqlite_meta.tables[table_name].create(bind=postgres_engine)
    else:
        raise ValueError(f"Schema for table '{table_name}' was not found in models or SQLite.")


def migrate_table(table_name: str):
    """Creates the table if missing and inserts new records into Neon Postgres."""
    if table_name not in sqlite_meta.tables:
        print(f"Skipping '{table_name}' (not found in local SQLite database).")
        return

    # Ensure target table exists in Postgres
    ensure_table_exists(table_name)

    sqlite_table = sqlite_meta.tables[table_name]

    # Read rows from SQLite
    with sqlite_engine.connect() as sqlite_conn:
        rows = sqlite_conn.execute(sqlite_table.select()).fetchall()

    if not rows:
        print(f"Table '{table_name}' is empty in SQLite. Skipping rows.")
        return

    keys = sqlite_table.columns.keys()
    data_to_insert = [dict(zip(keys, row)) for row in rows]

    # Reflect the target Postgres table to handle primary key conflicts safely
    pg_meta = MetaData()
    pg_table = MetaData().reflect(bind=postgres_engine, only=[table_name])
    pg_table = pg_meta.tables.get(table_name)

    if pg_table is None:
        pg_meta.reflect(bind=postgres_engine, only=[table_name])
        pg_table = pg_meta.tables[table_name]

    print(f"Syncing {len(data_to_insert)} rows for table: '{table_name}'...")

    with postgres_engine.begin() as pg_conn:
        # Use PostgreSQL ON CONFLICT DO NOTHING to skip existing records
        stmt = pg_insert(pg_table).values(data_to_insert)
        stmt = stmt.on_conflict_do_nothing()
        result = pg_conn.execute(stmt)
        print(f"Inserted {result.rowcount} new rows into '{table_name}'.")

        # Reset the Postgres auto-increment sequence so future app inserts don't collide
        pk_cols = [col.name for col in pg_table.primary_key.columns]
        if len(pk_cols) == 1 and pk_cols[0] == "id":
            seq_query = text(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true);"
            )
            pg_conn.execute(seq_query)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite tables and records to Neon PostgreSQL.")
    parser.add_argument(
        "tables",
        nargs="*",
        help="Specific table name(s) to create and migrate (e.g., py migrate.py kpis). Defaults to all tables.",
    )
    args = parser.parse_args()

    target_tables = args.tables if args.tables else DEFAULT_TABLES

    print("Starting data migration...")
    for table in target_tables:
        migrate_table(table)

    print("🎉 Migration completed successfully!")
