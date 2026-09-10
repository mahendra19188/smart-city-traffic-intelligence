import os

from dotenv import load_dotenv
import snowflake.connector


load_dotenv()


connection = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE")
)

cursor = connection.cursor()

cursor.execute("""
    SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()
""")

result = cursor.fetchone()

print("Snowflake connection successful!")
print("User       :", result[0])
print("Role       :", result[1])
print("Warehouse  :", result[2])
print("Database   :", result[3])
print("Schema     :", result[4])

cursor.close()
connection.close()