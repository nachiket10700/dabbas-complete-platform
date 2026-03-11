#!/usr/bin/env python3
"""
Dabba's Main Application Entry Point
"""

import os
import sys
import logging
import secrets
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, session, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the absolute path to the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(backend_dir, 'logs')

# Create logs directory if it doesn't exist
os.makedirs(logs_dir, exist_ok=True)

# Configure logging with UTF-8 encoding for Windows compatibility
log_file = os.path.join(logs_dir, 'app.log')

# Custom handler to handle Unicode on Windows
class UnicodeStreamHandler(logging.StreamHandler):
    """Handler that ensures Unicode is properly encoded for Windows console"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Replace emoji with text equivalents for Windows console
            msg = msg.replace('✅', '[SUCCESS]')
            msg = msg.replace('❌', '[ERROR]')
            msg = msg.replace('🚀', '[START]')
            msg = msg.replace('📝', '[LOG]')
            msg = msg.replace('💾', '[DB]')
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # Use UTF-8 for file
        UnicodeStreamHandler(sys.stdout)  # Use custom handler for console
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('APP_SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 24)))
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database/dabbas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Apply proxy fix for production
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Enable CORS
CORS(app, supports_credentials=True, origins=[
    'https://dabbas.com', 
    'http://localhost:8000', 
    'http://127.0.0.1:5500',
    'http://localhost:5500',
    'http://192.168.1.5:5500'
])

# Initialize JWT
jwt = JWTManager(app)

# Rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"],
    storage_uri="memory://"
)

# ============================================================================
# Import Models and Services
# ============================================================================

# Create database directory if it doesn't exist
db_dir = os.path.join(backend_dir, 'database')
os.makedirs(db_dir, exist_ok=True)

# Initialize database
def init_database():
    """Initialize SQLite database with required tables"""
    try:
        db_path = os.path.join(db_dir, 'dabbas.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                profile_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user_interactions table for recommendations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                meal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create meals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT,
                price REAL,
                provider_id INTEGER,
                ingredients TEXT,
                is_vegetarian BOOLEAN DEFAULT 0,
                is_popular BOOLEAN DEFAULT 0,
                reorder_frequency INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

# Initialize database
init_database()

# User models
class User:
    def create_user(self, username, email, password, role, profile_data=None):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Hash password (simple hash for demo - use proper hashing in production)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO users (username, email, password, role, phone, profile_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, role, profile_data.get('phone') if profile_data else None, json.dumps(profile_data) if profile_data else None))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {'success': True, 'user_id': user_id}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Username or email already exists'}
        except Exception as e:
            logger.error(f"User creation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def authenticate(self, email, password):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute('''
                SELECT id, username, email, role, phone, profile_data 
                FROM users WHERE email = ? AND password = ?
            ''', (email, password_hash))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                profile = json.loads(user[5]) if user[5] else {}
                return {
                    'success': True,
                    'user_id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3],
                    'phone': user[4],
                    'profile': profile
                }
            return {'success': False, 'error': 'Invalid credentials'}
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_user_by_id(self, user_id):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, role, phone, profile_data, created_at
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                profile = json.loads(user[5]) if user[5] else {}
                return {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[3],
                    'phone': user[4],
                    'profile': profile,
                    'created_at': user[6]
                }
            return None
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return None
    
    def update_user(self, user_id, data):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get existing profile
            cursor.execute('SELECT profile_data FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            profile = json.loads(result[0]) if result and result[0] else {}
            
            # Update profile with new data
            profile.update(data)
            
            cursor.execute('''
                UPDATE users 
                SET profile_data = ?
                WHERE id = ?
            ''', (json.dumps(profile), user_id))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Profile updated successfully'}
        except Exception as e:
            logger.error(f"Update user error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_users_by_role(self, role):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, phone, profile_data
                FROM users WHERE role = ?
            ''', (role,))
            
            users = cursor.fetchall()
            conn.close()
            
            result = []
            for user in users:
                profile = json.loads(user[4]) if user[4] else {}
                result.append({
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'phone': user[3],
                    'profile': profile
                })
            return result
        except Exception as e:
            logger.error(f"Get users by role error: {str(e)}")
            return []

class CustomerManager:
    def get_preferences(self, user_id):
        user = User().get_user_by_id(user_id)
        if user and 'profile' in user:
            return user['profile'].get('preferences', {
                'favorite_cuisines': [],
                'preferred_ingredients': [],
                'dietary_restrictions': [],
                'language': 'en'
            })
        return {
            'favorite_cuisines': [],
            'preferred_ingredients': [],
            'dietary_restrictions': [],
            'language': 'en'
        }
    
    def save_preferences(self, user_id, preferences):
        try:
            user = User()
            user.update_user(user_id, {'preferences': preferences})
            return {'success': True, 'message': 'Preferences saved successfully'}
        except Exception as e:
            logger.error(f"Save preferences error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_recent_orders(self, user_id, limit=10):
        # Mock data for now
        return []
    
    def get_orders(self, user_id, page=1, limit=10):
        return []
    
    def get_order_details(self, order_id, user_id):
        return None

class ProviderManager:
    def register_provider(self, user_id, business_details):
        try:
            user = User()
            user.update_user(user_id, {'business': business_details, 'status': 'pending'})
            return {'success': True, 'message': 'Provider registered successfully'}
        except Exception as e:
            logger.error(f"Provider registration error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_provider_stats(self, provider_id):
        return {
            'total_orders': 0,
            'total_revenue': 0,
            'average_rating': 0,
            'active_subscribers': 0
        }
    
    def get_today_orders(self, provider_id):
        return []
    
    def get_menu(self, provider_id):
        return []
    
    def add_menu_item(self, provider_id, data):
        return {'success': True, 'message': 'Menu item added', 'item_id': 1}
    
    def update_menu_item(self, provider_id, item_id, data):
        return {'success': True, 'message': 'Menu item updated'}
    
    def delete_menu_item(self, provider_id, item_id):
        return {'success': True, 'message': 'Menu item deleted'}
    
    def get_orders(self, provider_id, status=None, date=None):
        return []
    
    def update_order_status(self, provider_id, order_id, status):
        return {'success': True, 'message': 'Order status updated', 'customer_id': 1}
    
    def get_earnings(self, provider_id, period='month'):
        return {'total': 0, 'period': period}
    
    def get_providers_by_city(self, city):
        return []
    
    def get_nearby_providers(self, lat, lng, radius):
        return []
    
    def search_providers(self, query='', city='', cuisine=''):
        return []
    
    def search_menu_items(self, query='', cuisine=''):
        return []

class OwnerManager:
    def notify_new_provider(self, provider_id, business_name):
        logger.info(f"New provider registered: {business_name} (ID: {provider_id})")
    
    def get_platform_stats(self):
        return {
            'total_users': 0,
            'total_providers': 0,
            'total_orders': 0,
            'total_revenue': 0,
            'pending_verifications': 0
        }
    
    def get_providers(self, status=None, verified=None):
        return []
    
    def verify_provider(self, provider_id):
        return {'success': True, 'message': 'Provider verified'}
    
    def reject_provider(self, provider_id, reason):
        return {'success': True, 'message': 'Provider rejected'}
    
    def get_customers(self, page=1, limit=20):
        return []
    
    def get_settings(self):
        return {'platform_name': 'Dabba', 'currency': 'INR'}
    
    def update_settings(self, data):
        return {'success': True, 'message': 'Settings updated'}

class PaymentProcessor:
    def create_payment_order(self, amount, currency='INR', receipt=None):
        import uuid
        return {
            'success': True,
            'order_id': str(uuid.uuid4()),
            'amount': amount,
            'currency': currency
        }
    
    def save_order(self, order_data):
        logger.info(f"Payment order saved: {order_data}")
    
    def verify_payment(self, order_id, payment_id, signature):
        return {'success': True, 'message': 'Payment verified'}
    
    def verify_webhook_signature(self, data, signature):
        return True
    
    def update_payment_status(self, payment_id, status):
        logger.info(f"Payment {payment_id} status updated to {status}")

class SubscriptionManager:
    def get_user_subscriptions(self, user_id):
        return []
    
    def create_subscription(self, user_id, plan_type, provider_id=None):
        return {
            'success': True,
            'plan': {'id': 1, 'type': plan_type},
            'subscription_id': 1
        }
    
    def cancel_subscription(self, subscription_id):
        return {'success': True, 'message': 'Subscription cancelled'}
    
    def activate_subscription(self, subscription_id):
        logger.info(f"Subscription {subscription_id} activated")

class ComplaintManager:
    def create_complaint(self, user_id, user_role, data):
        import uuid
        complaint_id = str(uuid.uuid4())
        return {
            'success': True,
            'complaint_id': complaint_id,
            'message': 'Complaint created'
        }
    
    def get_complaints(self, user_id=None, provider_id=None, status=None, priority=None, limit=None):
        return []
    
    def get_complaint_details(self, complaint_id):
        return {
            'id': complaint_id,
            'user_id': 1,
            'provider_id': 1,
            'status': 'open',
            'messages': []
        }
    
    def add_message(self, complaint_id, user_id, user_role, message, attachments=None):
        return {'success': True, 'message': 'Message added'}
    
    def escalate_complaint(self, complaint_id, escalated_by, reason):
        return {'success': True, 'message': 'Complaint escalated'}
    
    def resolve_complaint(self, complaint_id, resolution, resolved_by):
        return {'success': True, 'message': 'Complaint resolved'}

class TranslationManager:
    def __init__(self):
        self.supported_languages = ['en', 'hi', 'gu', 'mr', 'ta', 'te', 'kn', 'ml']
    
    def get_available_languages(self):
        return [
            {'code': 'en', 'name': 'English'},
            {'code': 'hi', 'name': 'हिन्दी'},
            {'code': 'gu', 'name': 'ગુજરાતી'},
            {'code': 'mr', 'name': 'मराठी'},
            {'code': 'ta', 'name': 'தமிழ்'},
            {'code': 'te', 'name': 'తెలుగు'},
            {'code': 'kn', 'name': 'ಕನ್ನಡ'},
            {'code': 'ml', 'name': 'മലയാളം'}
        ]
    
    def translate(self, text, language='en', **kwargs):
        return text

class RegionalContentManager:
    def get_cities(self):
        return ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad']
    
    def get_areas(self, city):
        return ['Area 1', 'Area 2', 'Area 3']
    
    def get_region_info(self, city):
        return {
            'name': city.title(),
            'capital': city.title(),
            'language': 'en',
            'currency': 'INR',
            'timezone': 'Asia/Kolkata'
        }
    
    def get_festive_special(self, language):
        return []
    
    def get_local_recommendations(self, city, time_of_day):
        return []

# ============================================================================
# RECOMMENDATION SERVICE
# ============================================================================

class RecommendationEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_recommendations(self, user_id, preferences, order_history, city, time_of_day, limit=10):
        # Mock recommendations
        recommendations = []
        for i in range(min(limit, 5)):
            recommendations.append({
                'id': i,
                'name': f'Recommended Meal {i+1}',
                'cuisine': 'Indian',
                'price': 150 + i*50,
                'ingredients': ['Rice', 'Dal', 'Vegetables'],
                'is_vegetarian': True,
                'is_popular': i < 3,
                'reorder_frequency': i
            })
        return recommendations
    
    def explore_recommendations(self, user_id, preferences, history, limit=5):
        return self.get_recommendations(user_id, preferences, [], '', '', limit)
    
    def get_similar_items(self, meal_id, user_id, limit=5):
        return self.get_recommendations(user_id, {}, [], '', '', limit)
    
    def get_popular_items(self, city, limit=10):
        return self.get_recommendations(None, {}, [], city, '', limit)
    
    def get_trending_items(self, city, limit=10):
        return self.get_recommendations(None, {}, [], city, '', limit)
    
    def record_interaction(self, user_id, meal_id, liked, rating, context):
        try:
            db_path = os.path.join(db_dir, 'dabbas.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            action = 'like' if liked else 'dislike'
            cursor.execute('''
                INSERT INTO user_interactions (user_id, meal_id, action)
                VALUES (?, ?, ?)
            ''', (user_id, meal_id, action))
            
            conn.commit()
            conn.close()
            self.logger.info(f"Interaction recorded for user {user_id}, meal {meal_id}")
        except Exception as e:
            self.logger.error(f"Failed to record interaction: {str(e)}")

class EmailService:
    def send_welcome_email(self, email, username):
        logger.info(f"Welcome email sent to {email}")
    
    def send_welcome_sms(self, phone, username):
        logger.info(f"Welcome SMS sent to {phone}")
    
    def send_password_reset(self, email, reset_link):
        logger.info(f"Password reset email sent to {email} with link: {reset_link}")
    
    def send_provider_registration_confirmation(self, email, business_name):
        logger.info(f"Provider registration confirmation sent to {email}")
    
    def send_subscription_confirmation(self, email, username, plan):
        logger.info(f"Subscription confirmation sent to {email}")
    
    def send_provider_verification_confirmation(self, email, business_name):
        logger.info(f"Provider verification confirmation sent to {email}")
    
    def send_provider_rejection_notification(self, email, business_name, reason):
        logger.info(f"Provider rejection notification sent to {email}")
    
    def send_payment_confirmation(self, email, payment_id, amount):
        logger.info(f"Payment confirmation sent to {email}")
    
    def send_complaint_confirmation(self, email, complaint_id):
        logger.info(f"Complaint confirmation sent to {email}")
    
    def send_new_complaint_notification(self, email, complaint_id):
        logger.info(f"New complaint notification sent to {email}")
    
    def send_complaint_update(self, email, complaint_id):
        logger.info(f"Complaint update sent to {email}")
    
    def send_complaint_resolved(self, email, complaint_id, resolution):
        logger.info(f"Complaint resolved notification sent to {email}")
    
    def send_complaint_resolved_provider(self, email, complaint_id, resolution):
        logger.info(f"Complaint resolved notification sent to provider {email}")
    
    def send_escalated_complaint_notification(self, email, complaint_id):
        logger.info(f"Escalated complaint notification sent to {email}")
    
    def send_contact_form(self, name, email, phone, message):
        logger.info(f"Contact form received from {name} ({email})")
    
    def send_contact_auto_reply(self, email, name):
        logger.info(f"Contact auto-reply sent to {email}")

class SMSService:
    def send_welcome_sms(self, phone, username):
        logger.info(f"Welcome SMS sent to {phone}")
    
    def send_order_status_update(self, phone, order_id, status):
        logger.info(f"Order status update SMS sent to {phone}")
    
    def send_verification_sms(self, phone, business_name):
        logger.info(f"Verification SMS sent to {phone}")

# ============================================================================
# Initialize Services
# ============================================================================

# Initialize user-related services
user_model = User()
customer_manager = CustomerManager()
provider_manager = ProviderManager()
owner_manager = OwnerManager()

# Initialize payment services
payment_processor = PaymentProcessor()
subscription_manager = SubscriptionManager()

# Initialize complaint service
complaint_manager = ComplaintManager()

# Initialize localization services
translation_manager = TranslationManager()
regional_manager = RegionalContentManager()

# ============================================================================
# INITIALIZE RECOMMENDATION ENGINE
# ============================================================================

try:
    recommendation_engine = RecommendationEngine()
    logger.info("Recommendation Engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Recommendation Engine: {str(e)}")
    recommendation_engine = RecommendationEngine()

# Initialize communication services
email_service = EmailService()
sms_service = SMSService()

# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'environment': os.getenv('APP_ENV', 'development'),
        'services': {
            'recommendation_engine': 'active' if recommendation_engine else 'degraded'
        }
    }), 200

# ============================================================================
# Helper Functions for Recommendations
# ============================================================================

def get_current_meal_time():
    """Determine current meal time based on hour"""
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return 'breakfast'
    elif 11 <= hour < 15:
        return 'lunch'
    elif 15 <= hour < 18:
        return 'snack'
    else:
        return 'dinner'

def get_user_interaction_history(user_id, limit=50):
    """Get user's interaction history for bandit algorithm"""
    try:
        db_path = os.path.join(db_dir, 'dabbas.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT meal_id, action, created_at 
            FROM user_interactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        history = cursor.fetchall()
        conn.close()
        
        return [{
            'meal_id': h[0],
            'action': h[1],
            'timestamp': h[2]
        } for h in history]
    except Exception as e:
        logger.error(f"Error getting user interaction history: {str(e)}")
        return []

def generate_explanation(meal, preferences):
    """Generate human-readable explanation for recommendation"""
    explanations = []
    
    if meal.get('cuisine') in preferences.get('favorite_cuisines', []):
        explanations.append(f"Because you love {meal['cuisine']} cuisine")
    
    user_ingredients = set(preferences.get('preferred_ingredients', []))
    meal_ingredients = set(meal.get('ingredients', []))
    matches = user_ingredients.intersection(meal_ingredients)
    
    if matches:
        explanations.append(f"Contains your favorite: {', '.join(list(matches)[:2])}")
    
    if preferences.get('dietary_restrictions'):
        if meal.get('is_vegetarian') and 'vegetarian' in preferences['dietary_restrictions']:
            explanations.append("Vegetarian option")
    
    if meal.get('is_popular'):
        explanations.append("Popular in your area")
    
    if meal.get('reorder_frequency', 0) > 3:
        explanations.append("You've ordered this before")
    
    return ' • '.join(explanations) if explanations else "Recommended for you"

# ============================================================================
# RECOMMENDATION ENDPOINTS
# ============================================================================

@app.route('/api/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    try:
        user_id = get_jwt_identity()
        preferences = customer_manager.get_preferences(user_id)
        order_history = customer_manager.get_recent_orders(user_id, limit=10)
        city = request.args.get('city', 'mumbai')
        time_of_day = request.args.get('time', get_current_meal_time())
        limit = int(request.args.get('limit', 10))
        
        logger.info(f"Generating recommendations for user {user_id} in {city} at {time_of_day}")
        
        recommendations = recommendation_engine.get_recommendations(
            user_id=user_id,
            preferences=preferences,
            order_history=order_history,
            city=city,
            time_of_day=time_of_day,
            limit=limit
        )
        
        for rec in recommendations:
            region_info = regional_manager.get_region_info(city)
            rec['explanation'] = generate_explanation(rec, preferences)
            user_lang = preferences.get('language', 'en')
            rec['regional_note'] = translation_manager.translate(
                'recommendations.regional_special',
                language=user_lang,
                region=region_info.get('capital', city)
            )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations),
            'context': {'city': city, 'time_of_day': time_of_day, 'personalized': True}
        }), 200
        
    except Exception as e:
        logger.error(f"Get recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get recommendations'}), 500

@app.route('/api/recommendations/explore', methods=['GET'])
@jwt_required()
def get_explore_recommendations():
    try:
        user_id = get_jwt_identity()
        preferences = customer_manager.get_preferences(user_id)
        interaction_history = get_user_interaction_history(user_id)
        
        recommendations = recommendation_engine.explore_recommendations(
            user_id=user_id,
            preferences=preferences,
            history=interaction_history,
            limit=int(request.args.get('limit', 5))
        )
        
        return jsonify({'success': True, 'recommendations': recommendations, 'type': 'exploration'}), 200
        
    except Exception as e:
        logger.error(f"Explore recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get exploration recommendations'}), 500

@app.route('/api/recommendations/similar/<meal_id>', methods=['GET'])
@jwt_required()
def get_similar_recommendations(meal_id):
    try:
        user_id = get_jwt_identity()
        similar_meals = recommendation_engine.get_similar_items(
            meal_id=meal_id,
            user_id=user_id,
            limit=int(request.args.get('limit', 5))
        )
        
        return jsonify({'success': True, 'meal_id': meal_id, 'similar_meals': similar_meals}), 200
        
    except Exception as e:
        logger.error(f"Similar recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get similar meals'}), 500

@app.route('/api/recommendations/popular', methods=['GET'])
def get_popular_recommendations():
    try:
        city = request.args.get('city', 'mumbai')
        limit = int(request.args.get('limit', 10))
        popular_meals = recommendation_engine.get_popular_items(city=city, limit=limit)
        return jsonify({'success': True, 'recommendations': popular_meals, 'type': 'popular'}), 200
    except Exception as e:
        logger.error(f"Popular recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get popular recommendations'}), 500

@app.route('/api/recommendations/trending', methods=['GET'])
def get_trending_recommendations():
    try:
        city = request.args.get('city', 'mumbai')
        limit = int(request.args.get('limit', 10))
        trending = recommendation_engine.get_trending_items(city=city, limit=limit)
        return jsonify({'success': True, 'recommendations': trending, 'type': 'trending'}), 200
    except Exception as e:
        logger.error(f"Trending recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get trending recommendations'}), 500

@app.route('/api/recommendations/feedback', methods=['POST'])
@jwt_required()
def submit_recommendation_feedback():
    try:
        user_id = get_jwt_identity()
        data = request.json
        meal_id = data.get('meal_id')
        liked = data.get('liked')
        rating = data.get('rating')
        context = data.get('context', {})
        
        recommendation_engine.record_interaction(
            user_id=user_id,
            meal_id=meal_id,
            liked=liked,
            rating=rating,
            context=context
        )
        
        return jsonify({'success': True, 'message': 'Feedback recorded. Thank you!'}), 200
    except Exception as e:
        logger.error(f"Feedback submission error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to record feedback'}), 500

# ============================================================================
# Language & Localization Endpoints
# ============================================================================

@app.route('/api/languages', methods=['GET'])
def get_languages():
    languages = translation_manager.get_available_languages()
    return jsonify({'success': True, 'languages': languages})

@app.route('/api/cities', methods=['GET'])
def get_cities():
    cities = regional_manager.get_cities()
    return jsonify({'success': True, 'cities': cities})

@app.route('/api/cities/<city>/areas', methods=['GET'])
def get_city_areas(city):
    areas = regional_manager.get_areas(city)
    return jsonify({'success': True, 'city': city, 'areas': areas})

@app.route('/api/region/<city>', methods=['GET'])
def get_region_info(city):
    region = regional_manager.get_region_info(city)
    festive = regional_manager.get_festive_special(region.get('language'))
    return jsonify({'success': True, 'region': region, 'festive_special': festive})

@app.route('/api/local-recommendations', methods=['GET'])
def get_local_recommendations():
    city = request.args.get('city', 'mumbai')
    time_of_day = request.args.get('time', get_current_meal_time())
    recommendations = regional_manager.get_local_recommendations(city, time_of_day)
    return jsonify({'success': True, 'city': city, 'time_of_day': time_of_day, 'recommendations': recommendations})

# ============================================================================
# Customer Endpoints
# ============================================================================

@app.route('/api/customer/register', methods=['POST'])
@limiter.limit("5 per minute")
def customer_register():
    try:
        data = request.json
        required_fields = ['username', 'email', 'password', 'phone']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        result = user_model.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            role='customer',
            profile_data={
                'phone': data['phone'],
                'address': data.get('address', ''),
                'city': data.get('city', ''),
                'preferred_language': data.get('language', 'en')
            }
        )
        
        if result['success']:
            access_token = create_access_token(
                identity=result['user_id'],
                additional_claims={'role': 'customer'}
            )
            
            try:
                email_service.send_welcome_email(data['email'], data['username'])
                sms_service.send_welcome_sms(data['phone'], data['username'])
            except Exception as e:
                logger.error(f"Welcome notification failed: {str(e)}")
            
            return jsonify({
                'success': True,
                'token': access_token,
                'user_id': result['user_id'],
                'username': data['username'],
                'message': 'Registration successful'
            }), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/customer/login', methods=['POST'])
@limiter.limit("10 per minute")
def customer_login():
    try:
        data = request.json
        if 'email' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        result = user_model.authenticate(data['email'], data['password'])
        
        if result['success']:
            access_token = create_access_token(
                identity=result['user_id'],
                additional_claims={'role': 'customer'}
            )
            result['token'] = access_token
            preferences = customer_manager.get_preferences(result['user_id'])
            result['preferences'] = preferences
            return jsonify(result), 200
        else:
            return jsonify(result), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/customer/profile', methods=['GET'])
@jwt_required()
def get_customer_profile():
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        preferences = customer_manager.get_preferences(user_id)
        subscriptions = subscription_manager.get_user_subscriptions(user_id)
        orders = customer_manager.get_recent_orders(user_id, limit=5)
        
        return jsonify({
            'success': True,
            'profile': user,
            'preferences': preferences,
            'subscriptions': subscriptions,
            'recent_orders': orders
        }), 200
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load profile'}), 500

@app.route('/api/customer/profile', methods=['PUT'])
@jwt_required()
def update_customer_profile():
    try:
        user_id = get_jwt_identity()
        data = request.json
        result = user_model.update_user(user_id, data)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update profile'}), 500

@app.route('/api/customer/preferences', methods=['POST'])
@jwt_required()
def save_customer_preferences():
    try:
        user_id = get_jwt_identity()
        data = request.json
        result = customer_manager.save_preferences(user_id, data)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Save preferences error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to save preferences'}), 500

@app.route('/api/customer/subscriptions', methods=['GET'])
@jwt_required()
def get_customer_subscriptions():
    try:
        user_id = get_jwt_identity()
        subscriptions = subscription_manager.get_user_subscriptions(user_id)
        return jsonify({'success': True, 'subscriptions': subscriptions}), 200
    except Exception as e:
        logger.error(f"Get subscriptions error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load subscriptions'}), 500

@app.route('/api/customer/subscribe', methods=['POST'])
@jwt_required()
def create_subscription():
    try:
        user_id = get_jwt_identity()
        data = request.json
        if 'plan_type' not in data:
            return jsonify({'success': False, 'error': 'Plan type required'}), 400
        
        provider_id = data.get('provider_id')
        result = subscription_manager.create_subscription(
            user_id=user_id,
            plan_type=data['plan_type'],
            provider_id=provider_id
        )
        
        if result['success']:
            user = user_model.get_user_by_id(user_id)
            email_service.send_subscription_confirmation(
                user['email'],
                user['username'],
                result['plan']
            )
        
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Create subscription error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create subscription'}), 500

@app.route('/api/customer/subscription/<subscription_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(subscription_id):
    try:
        user_id = get_jwt_identity()
        subscriptions = subscription_manager.get_user_subscriptions(user_id)
        if not any(s['id'] == subscription_id for s in subscriptions):
            return jsonify({'success': False, 'error': 'Subscription not found'}), 404
        
        result = subscription_manager.cancel_subscription(subscription_id)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Cancel subscription error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to cancel subscription'}), 500

@app.route('/api/customer/orders', methods=['GET'])
@jwt_required()
def get_customer_orders():
    try:
        user_id = get_jwt_identity()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        orders = customer_manager.get_orders(user_id, page=page, limit=limit)
        return jsonify({'success': True, 'orders': orders, 'page': page, 'limit': limit}), 200
    except Exception as e:
        logger.error(f"Get orders error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load orders'}), 500

@app.route('/api/customer/order/<order_id>', methods=['GET'])
@jwt_required()
def get_order_details(order_id):
    try:
        user_id = get_jwt_identity()
        order = customer_manager.get_order_details(order_id, user_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        return jsonify({'success': True, 'order': order}), 200
    except Exception as e:
        logger.error(f"Get order details error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load order details'}), 500

# ============================================================================
# Provider Endpoints
# ============================================================================

@app.route('/api/provider/register', methods=['POST'])
@limiter.limit("3 per hour")
def provider_register():
    try:
        data = request.json
        required_fields = ['username', 'email', 'password', 'phone', 'business_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        result = user_model.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            role='provider',
            profile_data={
                'phone': data['phone'],
                'business_name': data['business_name'],
                'status': 'pending'
            }
        )
        
        if result['success']:
            provider_result = provider_manager.register_provider(
                user_id=result['user_id'],
                business_details=data
            )
            
            if provider_result['success']:
                owner_manager.notify_new_provider(result['user_id'], data['business_name'])
                email_service.send_provider_registration_confirmation(
                    data['email'],
                    data['business_name']
                )
                return jsonify({
                    'success': True,
                    'user_id': result['user_id'],
                    'message': 'Provider registered successfully. Pending verification.'
                }), 201
            else:
                return jsonify(provider_result), 400
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Provider registration error: {str(e)}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500

@app.route('/api/provider/login', methods=['POST'])
@limiter.limit("10 per minute")
def provider_login():
    try:
        data = request.json
        if 'email' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        result = user_model.authenticate(data['email'], data['password'])
        
        if result['success'] and result['role'] == 'provider':
            access_token = create_access_token(
                identity=result['user_id'],
                additional_claims={'role': 'provider'}
            )
            result['token'] = access_token
            stats = provider_manager.get_provider_stats(result['user_id'])
            result['stats'] = stats
            return jsonify(result), 200
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials or not a provider account'}), 401
    except Exception as e:
        logger.error(f"Provider login error: {str(e)}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500

@app.route('/api/provider/dashboard', methods=['GET'])
@jwt_required()
def provider_dashboard():
    try:
        provider_id = get_jwt_identity()
        stats = provider_manager.get_provider_stats(provider_id)
        today_orders = provider_manager.get_today_orders(provider_id)
        menu = provider_manager.get_menu(provider_id)
        complaints = complaint_manager.get_complaints(provider_id=provider_id, limit=5)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'today_orders': today_orders,
            'menu': menu,
            'recent_complaints': complaints
        }), 200
    except Exception as e:
        logger.error(f"Provider dashboard error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

@app.route('/api/provider/menu', methods=['GET'])
@jwt_required()
def get_provider_menu():
    try:
        provider_id = get_jwt_identity()
        menu = provider_manager.get_menu(provider_id)
        return jsonify({'success': True, 'menu': menu}), 200
    except Exception as e:
        logger.error(f"Get menu error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load menu'}), 500

@app.route('/api/provider/menu', methods=['POST'])
@jwt_required()
def add_menu_item():
    try:
        provider_id = get_jwt_identity()
        data = request.json
        result = provider_manager.add_menu_item(provider_id, data)
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Add menu item error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to add menu item'}), 500

@app.route('/api/provider/menu/<item_id>', methods=['PUT'])
@jwt_required()
def update_menu_item(item_id):
    try:
        provider_id = get_jwt_identity()
        data = request.json
        result = provider_manager.update_menu_item(provider_id, item_id, data)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Update menu item error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update menu item'}), 500

@app.route('/api/provider/menu/<item_id>', methods=['DELETE'])
@jwt_required()
def delete_menu_item(item_id):
    try:
        provider_id = get_jwt_identity()
        result = provider_manager.delete_menu_item(provider_id, item_id)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Delete menu item error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to delete menu item'}), 500

@app.route('/api/provider/orders', methods=['GET'])
@jwt_required()
def get_provider_orders():
    try:
        provider_id = get_jwt_identity()
        status = request.args.get('status')
        date = request.args.get('date')
        orders = provider_manager.get_orders(provider_id, status=status, date=date)
        return jsonify({'success': True, 'orders': orders}), 200
    except Exception as e:
        logger.error(f"Get orders error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load orders'}), 500

@app.route('/api/provider/order/<order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    try:
        provider_id = get_jwt_identity()
        data = request.json
        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        result = provider_manager.update_order_status(provider_id, order_id, data['status'])
        
        if result['success']:
            customer_id = result.get('customer_id')
            if customer_id:
                customer = user_model.get_user_by_id(customer_id)
                if customer:
                    sms_service.send_order_status_update(
                        customer['phone'],
                        order_id,
                        data['status']
                    )
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Update order status error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update order status'}), 500

@app.route('/api/provider/earnings', methods=['GET'])
@jwt_required()
def get_provider_earnings():
    try:
        provider_id = get_jwt_identity()
        period = request.args.get('period', 'month')
        earnings = provider_manager.get_earnings(provider_id, period)
        return jsonify({'success': True, 'earnings': earnings}), 200
    except Exception as e:
        logger.error(f"Get earnings error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load earnings'}), 500

# ============================================================================
# Owner Endpoints
# ============================================================================

@app.route('/api/owner/login', methods=['POST'])
@limiter.limit("5 per minute")
def owner_login():
    try:
        data = request.json
        if 'email' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        result = user_model.authenticate(data['email'], data['password'])
        
        if result['success'] and result['role'] == 'owner':
            access_token = create_access_token(
                identity=result['user_id'],
                additional_claims={'role': 'owner'}
            )
            result['token'] = access_token
            stats = owner_manager.get_platform_stats()
            result['stats'] = stats
            return jsonify(result), 200
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials or not an owner account'}), 401
    except Exception as e:
        logger.error(f"Owner login error: {str(e)}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500

@app.route('/api/owner/stats', methods=['GET'])
@jwt_required()
def get_platform_stats():
    try:
        stats = owner_manager.get_platform_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        logger.error(f"Get platform stats error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load statistics'}), 500

@app.route('/api/owner/providers', methods=['GET'])
@jwt_required()
def get_providers():
    try:
        status = request.args.get('status')
        verified = request.args.get('verified')
        providers = owner_manager.get_providers(status=status, verified=verified)
        return jsonify({'success': True, 'providers': providers}), 200
    except Exception as e:
        logger.error(f"Get providers error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load providers'}), 500

@app.route('/api/owner/provider/<provider_id>/verify', methods=['POST'])
@jwt_required()
def verify_provider(provider_id):
    try:
        data = request.json
        action = data.get('action', 'verify')
        
        if action == 'verify':
            result = owner_manager.verify_provider(provider_id)
        elif action == 'reject':
            result = owner_manager.reject_provider(provider_id, data.get('reason'))
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        if result['success']:
            provider = user_model.get_user_by_id(provider_id)
            if provider:
                if action == 'verify':
                    email_service.send_provider_verification_confirmation(
                        provider['email'],
                        provider.get('profile', {}).get('business_name', 'Your business')
                    )
                    sms_service.send_verification_sms(
                        provider['phone'],
                        provider.get('profile', {}).get('business_name', 'Your business')
                    )
                else:
                    email_service.send_provider_rejection_notification(
                        provider['email'],
                        provider.get('profile', {}).get('business_name', 'Your business'),
                        data.get('reason')
                    )
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Verify provider error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to verify provider'}), 500

@app.route('/api/owner/customers', methods=['GET'])
@jwt_required()
def get_customers():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        customers = owner_manager.get_customers(page=page, limit=limit)
        return jsonify({'success': True, 'customers': customers, 'page': page, 'limit': limit}), 200
    except Exception as e:
        logger.error(f"Get customers error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load customers'}), 500

@app.route('/api/owner/complaints', methods=['GET'])
@jwt_required()
def get_all_complaints():
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        complaints = complaint_manager.get_complaints(status=status, priority=priority)
        return jsonify({'success': True, 'complaints': complaints}), 200
    except Exception as e:
        logger.error(f"Get all complaints error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load complaints'}), 500

@app.route('/api/owner/complaint/<complaint_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_complaint(complaint_id):
    try:
        owner_id = get_jwt_identity()
        data = request.json
        result = complaint_manager.resolve_complaint(
            complaint_id,
            data.get('resolution', ''),
            owner_id
        )
        
        if result['success']:
            complaint = complaint_manager.get_complaint_details(complaint_id)
            if complaint:
                customer = user_model.get_user_by_id(complaint['user_id'])
                if customer:
                    email_service.send_complaint_resolved(
                        customer['email'],
                        complaint_id,
                        data.get('resolution')
                    )
                
                if complaint.get('provider_id'):
                    provider = user_model.get_user_by_id(complaint['provider_id'])
                    if provider:
                        email_service.send_complaint_resolved_provider(
                            provider['email'],
                            complaint_id,
                            data.get('resolution')
                        )
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Resolve complaint error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to resolve complaint'}), 500

@app.route('/api/owner/settings', methods=['GET'])
@jwt_required()
def get_platform_settings():
    try:
        settings = owner_manager.get_settings()
        return jsonify({'success': True, 'settings': settings}), 200
    except Exception as e:
        logger.error(f"Get settings error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load settings'}), 500

@app.route('/api/owner/settings', methods=['PUT'])
@jwt_required()
def update_platform_settings():
    try:
        data = request.json
        result = owner_manager.update_settings(data)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Update settings error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update settings'}), 500

# ============================================================================
# Payment Endpoints
# ============================================================================

@app.route('/api/payment/create-order', methods=['POST'])
@jwt_required()
def create_payment_order():
    try:
        user_id = get_jwt_identity()
        data = request.json
        if 'amount' not in data:
            return jsonify({'success': False, 'error': 'Amount required'}), 400
        
        result = payment_processor.create_payment_order(
            amount=data['amount'],
            currency=data.get('currency', 'INR'),
            receipt=data.get('receipt')
        )
        
        if result['success']:
            payment_processor.save_order({
                'user_id': user_id,
                'order_id': result['order_id'],
                'amount': data['amount'],
                'status': 'created'
            })
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Create payment order error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create payment order'}), 500

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    try:
        data = request.json
        required_fields = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        result = payment_processor.verify_payment(
            data['razorpay_order_id'],
            data['razorpay_payment_id'],
            data['razorpay_signature']
        )
        
        if result['success']:
            if 'subscription_id' in data:
                subscription_manager.activate_subscription(data['subscription_id'])
            
            # Get user_id from JWT if available
            try:
                user_id = get_jwt_identity()
                if user_id:
                    user = user_model.get_user_by_id(user_id)
                    if user:
                        email_service.send_payment_confirmation(
                            user['email'],
                            data['razorpay_payment_id'],
                            data.get('amount', 0)
                        )
            except:
                pass  # No JWT token, skip email
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Verify payment error: {str(e)}")
        return jsonify({'success': False, 'error': 'Payment verification failed'}), 500

@app.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.json
        signature = request.headers.get('X-Razorpay-Signature')
        
        if not payment_processor.verify_webhook_signature(data, signature):
            return jsonify({'error': 'Invalid signature'}), 401
        
        event = data.get('event')
        payload = data.get('payload', {})
        
        if event == 'payment.captured':
            payment_id = payload.get('payment', {}).get('id')
            payment_processor.update_payment_status(payment_id, 'completed')
        elif event == 'payment.failed':
            payment_id = payload.get('payment', {}).get('id')
            payment_processor.update_payment_status(payment_id, 'failed')
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Payment webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

# ============================================================================
# Complaint Endpoints
# ============================================================================

@app.route('/api/complaints/create', methods=['POST'])
@jwt_required()
def create_complaint():
    try:
        user_id = get_jwt_identity()
        data = request.json
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        result = complaint_manager.create_complaint(
            user_id=user_id,
            user_role=user['role'],
            data=data
        )
        
        if result['success']:
            email_service.send_complaint_confirmation(
                user['email'],
                result['complaint_id']
            )
            
            if data.get('provider_id'):
                provider = user_model.get_user_by_id(data['provider_id'])
                if provider:
                    email_service.send_new_complaint_notification(
                        provider['email'],
                        result['complaint_id']
                    )
        
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Create complaint error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create complaint'}), 500

@app.route('/api/complaints', methods=['GET'])
@jwt_required()
def get_complaints():
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if user['role'] == 'customer':
            complaints = complaint_manager.get_complaints(user_id=user_id)
        elif user['role'] == 'provider':
            complaints = complaint_manager.get_complaints(provider_id=user_id)
        elif user['role'] == 'owner':
            complaints = complaint_manager.get_complaints()
        else:
            complaints = []
        
        return jsonify({'success': True, 'complaints': complaints}), 200
    except Exception as e:
        logger.error(f"Get complaints error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load complaints'}), 500

@app.route('/api/complaints/<complaint_id>', methods=['GET'])
@jwt_required()
def get_complaint_details(complaint_id):
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        
        complaint = complaint_manager.get_complaint_details(complaint_id)
        if not complaint:
            return jsonify({'success': False, 'error': 'Complaint not found'}), 404
        
        if user['role'] == 'customer' and complaint['user_id'] != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        if user['role'] == 'provider' and complaint.get('provider_id') != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        return jsonify({'success': True, 'complaint': complaint}), 200
    except Exception as e:
        logger.error(f"Get complaint details error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load complaint details'}), 500

@app.route('/api/complaints/<complaint_id>/message', methods=['POST'])
@jwt_required()
def add_complaint_message(complaint_id):
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        data = request.json
        
        if 'message' not in data:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        result = complaint_manager.add_message(
            complaint_id=complaint_id,
            user_id=user_id,
            user_role=user['role'],
            message=data['message'],
            attachments=data.get('attachments')
        )
        
        if result['success']:
            complaint = complaint_manager.get_complaint_details(complaint_id)
            if complaint:
                if user['role'] != 'customer':
                    customer = user_model.get_user_by_id(complaint['user_id'])
                    if customer:
                        email_service.send_complaint_update(
                            customer['email'],
                            complaint_id
                        )
                if user['role'] != 'provider' and complaint.get('provider_id'):
                    provider = user_model.get_user_by_id(complaint['provider_id'])
                    if provider:
                        email_service.send_complaint_update(
                            provider['email'],
                            complaint_id
                        )
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Add complaint message error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to add message'}), 500

@app.route('/api/complaints/<complaint_id>/escalate', methods=['POST'])
@jwt_required()
def escalate_complaint(complaint_id):
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        data = request.json
        
        if user['role'] not in ['customer', 'provider']:
            return jsonify({
                'success': False,
                'error': 'Only customers and providers can escalate complaints'
            }), 403
        
        result = complaint_manager.escalate_complaint(
            complaint_id=complaint_id,
            escalated_by=user_id,
            reason=data.get('reason', 'No reason provided')
        )
        
        if result['success']:
            owners = user_model.get_users_by_role('owner')
            for owner in owners:
                email_service.send_escalated_complaint_notification(
                    owner['email'],
                    complaint_id
                )
        
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Escalate complaint error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to escalate complaint'}), 500

# ============================================================================
# Provider Search Endpoints
# ============================================================================

@app.route('/api/providers/nearby', methods=['GET'])
def get_nearby_providers():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 4, type=int)
        
        if not lat or not lng:
            city = request.args.get('city', 'mumbai')
            providers = provider_manager.get_providers_by_city(city)
        else:
            providers = provider_manager.get_nearby_providers(lat, lng, radius)
        
        return jsonify({'success': True, 'providers': providers}), 200
    except Exception as e:
        logger.error(f"Get nearby providers error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get nearby providers'}), 500

# ============================================================================
# Search Endpoints
# ============================================================================

@app.route('/api/search', methods=['GET'])
def search():
    try:
        query = request.args.get('q', '')
        city = request.args.get('city', '')
        cuisine = request.args.get('cuisine', '')
        
        if not query and not cuisine:
            return jsonify({'success': False, 'error': 'Search query or cuisine required'}), 400
        
        providers = provider_manager.search_providers(query=query, city=city, cuisine=cuisine)
        menu_items = provider_manager.search_menu_items(query=query, cuisine=cuisine)
        
        return jsonify({'success': True, 'providers': providers, 'menu_items': menu_items}), 200
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'success': False, 'error': 'Search failed'}), 500

# ============================================================================
# Contact Endpoint
# ============================================================================

@app.route('/api/contact', methods=['POST'])
@limiter.limit("3 per hour")
def contact():
    try:
        data = request.json
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        email_service.send_contact_form(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone'),
            message=data['message']
        )
        email_service.send_contact_auto_reply(data['email'], data['name'])
        
        return jsonify({
            'success': True,
            'message': 'Thank you for contacting us. We will get back to you soon.'
        }), 200
    except Exception as e:
        logger.error(f"Contact form error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send message'}), 500

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Resource not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'success': False, 'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ============================================================================
# Before Request
# ============================================================================

@app.before_request
def before_request():
    language = request.headers.get('Accept-Language', 'en')
    if language not in translation_manager.supported_languages:
        language = 'en'
    g.language = language

# ============================================================================
# After Request
# ============================================================================

@app.after_request
def after_request(response):
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-Frame-Options', 'DENY')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Content-Language', g.get('language', 'en'))
    return response

# ============================================================================
# Home Route
# ============================================================================

@app.route("/")
def home():
    return {
        "success": True,
        "message": "Dabba's Backend Running"
    }

# ============================================================================
# Forgot Password Endpoints
# ============================================================================

@app.route('/api/customer/forgot-password', methods=['POST'])
def customer_forgot_password():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        
        reset_token = secrets.token_urlsafe(32)
        logger.info(f"Password reset token for {email}: {reset_token}")
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}&role=customer"
        email_service.send_password_reset(email, reset_link)
        
        return jsonify({'success': True, 'message': 'Reset link sent to your email'})
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/provider/forgot-password', methods=['POST'])
def provider_forgot_password():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        
        reset_token = secrets.token_urlsafe(32)
        logger.info(f"Provider password reset token for {email}: {reset_token}")
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}&role=provider"
        email_service.send_password_reset(email, reset_link)
        
        return jsonify({'success': True, 'message': 'Reset link sent to your email'})
    except Exception as e:
        logger.error(f"Provider forgot password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/owner/forgot-password', methods=['POST'])
def owner_forgot_password():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        
        reset_token = secrets.token_urlsafe(32)
        logger.info(f"Owner password reset token for {email}: {reset_token}")
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}&role=owner"
        email_service.send_password_reset(email, reset_link)
        
        return jsonify({'success': True, 'message': 'Reset link sent to your email'})
    except Exception as e:
        logger.error(f"Owner forgot password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        token = data.get('token')
        new_password = data.get('password')
        role = data.get('role')
        
        if not all([token, new_password, role]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        logger.info(f"Password reset attempt with token: {token} for role: {role}")
        return jsonify({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Test Database Route
# ============================================================================

@app.route('/api/test')
def test():
    try:
        db_path = os.path.join(db_dir, 'dabbas.db')
        conn = sqlite3.connect(db_path)
        conn.close()
        return jsonify({
            'success': True,
            'message': 'Database connected!',
            'database': os.environ.get('DATABASE_URL', 'sqlite:///database/dabbas.db')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Database error: {str(e)}'
        }), 500

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('APP_ENV') == 'development'
    
    logger.info(f"Starting Dabba's Backend on port {port}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Database: {os.path.join(db_dir, 'dabbas.db')}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )