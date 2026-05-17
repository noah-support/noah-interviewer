import os

from peewee import PostgresqlDatabase

db = PostgresqlDatabase(
    os.getenv("POSTGRES_DB", "noah"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "Newpassword"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5434")),
)
