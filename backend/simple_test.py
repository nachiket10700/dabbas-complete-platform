# simple_test.py
print("Testing database connection...")

try:
    from database import db
    conn = db.get_connection()
    print("✅ Database connected!")
    
    # Create a simple test table
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    print("✅ Test table created/verified")
    
    conn.close()
    print("\n✅ All good! Your database is working.")
    
except Exception as e:
    print(f"❌ Error: {e}")