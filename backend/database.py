from peewee import PostgresqlDatabase

db = PostgresqlDatabase(
    'noah',
    user='postgres',
    password='Newpassword',
    host='localhost',
    port=5434
)