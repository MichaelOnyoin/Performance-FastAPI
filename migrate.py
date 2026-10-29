import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker

# 1. Setup Engines
# Path to your local SQLite file
SQLITE_URL = "sqlite:///./data/performance.db" 
# Get your Neon URL from environment variables, or paste it here temporarily
POSTGRES_URL = os.environ.get("DB_URL", "postgresql://neondb_owner:npg_KgAM5tzUa4Go@ep-nameless-pine-b5v7srq8-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# Crucial for Neon/Postgres compatibility
if POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql://", 1)

sqlite_engine = create_engine(SQLITE_URL)
postgres_engine = create_engine(POSTGRES_URL)

# 2. Reflect SQLite Schema
sqlite_meta = MetaData()
sqlite_meta.reflect(bind=sqlite_engine)


# 3. Create Tables in Postgres
#print("Creating tables in Neon PostgreSQL...")
#from app.database import Base 

# CRUCIAL: You MUST import your models module here so SQLAlchemy 
# registers the __tablename__ definitions into the metadata!
#from app import models  # Or change to wherever your User, Employee models live

# Now this will successfully create "users", "employees", etc. in Neon
#Base.metadata.create_all(postgres_engine)


# 4. Migrate Data Table by Table
# Sequence matters because of Foreign Key constraints (Base tables first)
tables_in_order = ["users", "employees", "kpis", "entries", "employee_kpis"]

print("Starting data migration...")
for table_name in tables_in_order:
    if table_name not in sqlite_meta.tables:
        print(f"Skipping {table_name} (not found in SQLite)")
        continue
        
    sqlite_table = sqlite_meta.tables[table_name]
    
    # Read rows from SQLite
    with sqlite_engine.connect() as sqlite_conn:
        rows = sqlite_conn.execute(sqlite_table.select()).fetchall()
        
    if not rows:
        print(f"Table '{table_name}' is empty. Skipping rows.")
        continue

    # Convert rows to dictionaries
    keys = sqlite_table.columns.keys()
    data_to_insert = [dict(zip(keys, row)) for row in rows]

    # Write rows to Postgres
    print(f"Migrating {len(data_to_insert)} rows for table: '{table_name}'...")
    with postgres_engine.begin() as pg_conn:
        # Construct an explicit INSERT statement matching Postgres syntax
        placeholders = ", ".join([f":{key}" for key in keys])
        columns_str = ", ".join(keys)
        insert_stmt = text(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})")
        
        pg_conn.execute(insert_stmt, data_to_insert)

print("🎉 Migration completed successfully!")
