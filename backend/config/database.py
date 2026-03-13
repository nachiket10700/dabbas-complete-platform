# config/database.py
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="dabbas_provider",
            user="postgres",
            password="nachiket986088",  # CHANGE THIS to your actual password
            port="5432"
        )
        print("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def init_database():
    """Create tables if they don't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Create providers table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    id SERIAL PRIMARY KEY,
                    business_name VARCHAR(255) NOT NULL,
                    owner_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    business_address TEXT NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    cuisine VARCHAR(100),
                    password_hash VARCHAR(255) NOT NULL,
                    gst_number VARCHAR(50),
                    fssai_license VARCHAR(100),
                    is_verified BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Database tables created/verified")
            return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
    return False

def test_connection():
    """Test database connection"""
    print("🔍 Testing PostgreSQL connection...")
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"✅ PostgreSQL version: {version[0]}")
            
            cur.execute("SELECT NOW();")
            time = cur.fetchone()
            print(f"✅ Server time: {time[0]}")
            
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Query error: {e}")
            return False
    return False

# This runs only when file is executed directly
if __name__ == "__main__":
    test_connection()