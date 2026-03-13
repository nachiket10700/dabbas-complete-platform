# backend/api/provider.py
from flask import Blueprint, request, jsonify
import logging
import psycopg2
import psycopg2.extras
import hashlib
from datetime import datetime

provider_bp = Blueprint('provider', __name__, url_prefix='/api/provider')
logger = logging.getLogger(__name__)

# PostgreSQL connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="dabbas_provider",
            user="postgres",
            password="nachiket986088",  # CHANGE THIS TO YOUR POSTGRES PASSWORD
            port="5432"
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# Create tables if they don't exist
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Create providers table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    id SERIAL PRIMARY KEY,
                    business_name VARCHAR(255) NOT NULL,
                    owner_name VARCHAR(255),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    business_address TEXT,
                    city VARCHAR(100),
                    password_hash VARCHAR(255) NOT NULL,
                    gst_number VARCHAR(50),
                    fssai_license VARCHAR(100),
                    is_verified BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            logger.info("PostgreSQL tables initialized successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

# Initialize database on module load
init_db()

@provider_bp.route('/test', methods=['GET'])
def test():
    return jsonify({
        'success': True, 
        'message': 'Provider API is working with PostgreSQL!',
        'database': 'PostgreSQL'
    })

@provider_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        logger.info(f"Registration received for email: {data.get('email')}")
        
        # Validate required fields
        required = ['businessName', 'email', 'phone', 'password']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing {field}'}), 400
        
        # Extract password properly
        password = data['password']
        if isinstance(password, dict):
            if 'password' in password:
                password = password['password']
            elif 'value' in password:
                password = password['value']
            else:
                password = str(password)
        
        # Ensure password is string
        if not isinstance(password, str):
            password = str(password)
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Connect to PostgreSQL
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Insert data
        cur.execute("""
            INSERT INTO providers (
                business_name, owner_name, email, phone, 
                business_address, city, password_hash,
                gst_number, fssai_license
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, business_name, email, created_at
        """, (
            data['businessName'],
            data.get('ownerName', ''),
            data['email'],
            data['phone'],
            data.get('businessAddress', ''),
            data.get('city', ''),
            password_hash,
            data.get('gst', None),
            data.get('fssai', None)
        ))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Provider registered with ID: {result['id']}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'provider': {
                'id': result['id'],
                'business_name': result['business_name'],
                'email': result['email']
            }
        }), 201
        
    except psycopg2.IntegrityError as e:
        if 'email' in str(e):
            return jsonify({'success': False, 'error': 'Email already registered'}), 400
        elif 'phone' in str(e):
            return jsonify({'success': False, 'error': 'Phone number already registered'}), 400
        else:
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Registration error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/list', methods=['GET'])
def list_providers():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM providers ORDER BY created_at DESC")
        providers = cur.fetchall()
        cur.close()
        conn.close()
        
        provider_list = []
        for p in providers:
            provider_list.append({
                'id': p['id'],
                'business_name': p['business_name'],
                'owner_name': p['owner_name'],
                'email': p['email'],
                'phone': p['phone'],
                'business_address': p['business_address'],
                'city': p['city'],
                'is_verified': p['is_verified'],
                'created_at': p['created_at']
            })
        
        return jsonify({
            'success': True,
            'count': len(provider_list),
            'providers': provider_list
        })
        
    except Exception as e:
        logger.error(f"Error in list_providers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        # Extract password properly
        if isinstance(password, dict):
            if 'password' in password:
                password = password['password']
            elif 'value' in password:
                password = password['value']
            else:
                password = str(password)
        
        if not isinstance(password, str):
            password = str(password)
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("""
            SELECT * FROM providers 
            WHERE email = %s AND password_hash = %s
        """, (email, password_hash))
        
        provider = cur.fetchone()
        cur.close()
        conn.close()
        
        if provider:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'provider': {
                    'id': provider['id'],
                    'business_name': provider['business_name'],
                    'email': provider['email']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to check database connection"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()
            cur.close()
            conn.close()
            return jsonify({
                'success': True,
                'message': 'PostgreSQL connected',
                'version': version[0]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'PostgreSQL connection failed'
            }), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500