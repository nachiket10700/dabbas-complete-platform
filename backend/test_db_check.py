# test_db_check.py
import os  # ← Add this missing import!
from app import app
from database import db

print("Testing database connection...")
print(f"Database path: {db.db_path}")
print(f"Database exists: {os.path.exists(db.db_path)}")

try:
    conn = db.get_connection()
    print("✅ Successfully connected to database!")
    
    # List all tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n📋 Tables in database ({len(tables)}):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   - {table[0]}: {count} records")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")