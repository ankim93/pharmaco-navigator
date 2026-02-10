"""
Execute SQL file using Python
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Get database connection string from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

# Get SQL filename
if len(sys.argv) > 1:
    sql_filename = sys.argv[1]
else:
    sql_filename = 'insert_demo_patients.sql'

# Read SQL file
sql_file = Path(__file__).parent / sql_filename

if not sql_file.exists():
    print(f"ERROR: SQL file not found: {sql_file}")
    sys.exit(1)

print(f"Reading SQL from: {sql_file}")
sql_content = sql_file.read_text()

# Connect and execute
try:
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Executing SQL statements...")
    cursor.execute(sql_content)
    
    # Fetch results if any
    if cursor.description:
        rows = cursor.fetchall()
        print("\nGenomic profiles inserted successfully\n")
        print(f"{'Patient ID':<12} {'Gene':<10} {'Allele 1':<12} {'Allele 2':<12}")
        print("-" * 50)
        for row in rows:
            print(f"{row[0]:<12} {row[1]:<10} {row[2]:<12} {row[3]:<12}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\nSQL executed successfully")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
