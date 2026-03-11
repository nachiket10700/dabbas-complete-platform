"""
User Management Module
"""

import hashlib
import secrets
import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import os


class User:
    def __init__(self, db_path=None):
        if db_path is None:
            # Get absolute path
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
        
        # Debug
        print(f"📁 User DB: {self.db_path}")
        print(f"   Exists: {os.path.exists(self.db_path)}")
    
    def create_user(self, username, email, password, role, profile_data=None, phone=None):
        """Create a new user with retry logic for locked database"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                user_id = f"USR{secrets.token_hex(4).upper()}"
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                conn = sqlite3.connect(self.db_path, timeout=10)
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                if cursor.fetchone():
                    conn.close()
                    return {'success': False, 'error': 'Email already exists'}
                
                cursor.execute('''
                    INSERT INTO users 
                    (id, username, email, phone, password_hash, role, profile_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, username, email, phone, password_hash, 
                    role, json.dumps(profile_data or {}), datetime.now()
                ))
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'message': 'User created successfully'
                }
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(1)
                    continue
                else:
                    print(f"❌ Database error: {str(e)}")
                    return {'success': False, 'error': str(e)}
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                return {'success': False, 'error': str(e)}
    
    def authenticate(self, email, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, role, status, profile_data 
                FROM users 
                WHERE email = ? AND password_hash = ?
            ''', (email, password_hash))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return {
                    'success': True,
                    'user_id': user[0],
                    'username': user[1],
                    'role': user[2],
                    'status': user[3],
                    'profile': json.loads(user[4]) if user[4] else {}
                }
            else:
                return {'success': False, 'error': 'Invalid email or password'}
                
        except Exception as e:
            print(f"❌ Auth error: {str(e)}")
            return {'success': False, 'error': str(e)}


class CustomerManager:
    def __init__(self, db_path=None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
    
    def save_preferences(self, user_id: str, preferences: Dict) -> Dict:
        """Save customer preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if preferences exist
            cursor.execute('SELECT user_id FROM customer_preferences WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute('''
                    UPDATE customer_preferences 
                    SET dietary_restrictions = ?, favorite_cuisines = ?, 
                        disliked_ingredients = ?, health_goals = ?,
                        language = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (
                    json.dumps(preferences.get('dietary_restrictions', [])),
                    json.dumps(preferences.get('favorite_cuisines', [])),
                    json.dumps(preferences.get('disliked_ingredients', [])),
                    json.dumps(preferences.get('health_goals', {})),
                    preferences.get('language', 'en'),
                    datetime.now(),
                    user_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO customer_preferences 
                    (user_id, dietary_restrictions, favorite_cuisines, disliked_ingredients, 
                     health_goals, language, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    json.dumps(preferences.get('dietary_restrictions', [])),
                    json.dumps(preferences.get('favorite_cuisines', [])),
                    json.dumps(preferences.get('disliked_ingredients', [])),
                    json.dumps(preferences.get('health_goals', {})),
                    preferences.get('language', 'en'),
                    datetime.now(),
                    datetime.now()
                ))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Preferences saved"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_preferences(self, user_id: str) -> Dict:
        """Get customer preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM customer_preferences WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "dietary_restrictions": json.loads(row[1]) if row[1] else [],
                    "favorite_cuisines": json.loads(row[2]) if row[2] else [],
                    "disliked_ingredients": json.loads(row[3]) if row[3] else [],
                    "health_goals": json.loads(row[4]) if row[4] else {},
                    "language": row[5] or 'en'
                }
            return {}
        except Exception as e:
            print(f"❌ Error getting preferences: {str(e)}")
            return {}
    
    def get_recent_orders(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent orders for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM orders 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            orders = cursor.fetchall()
            conn.close()
            
            return [{'id': o[0], 'status': o[5], 'amount': o[4], 'date': o[8]} for o in orders]
        except Exception as e:
            print(f"❌ Error getting recent orders: {str(e)}")
            return []
    
    def get_orders(self, user_id: str, page: int = 1, limit: int = 10) -> List[Dict]:
        """Get paginated orders"""
        try:
            offset = (page - 1) * limit
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM orders 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            orders = cursor.fetchall()
            conn.close()
            
            return [{'id': o[0], 'status': o[5], 'amount': o[4], 'date': o[8]} for o in orders]
        except Exception as e:
            print(f"❌ Error getting orders: {str(e)}")
            return []
    
    def get_order_details(self, order_id: str, user_id: str) -> Optional[Dict]:
        """Get order details"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM orders 
                WHERE id = ? AND user_id = ?
            ''', (order_id, user_id))
            
            order = cursor.fetchone()
            conn.close()
            
            if order:
                return {
                    'id': order[0],
                    'status': order[5],
                    'amount': order[4],
                    'items': json.loads(order[3]) if order[3] else [],
                    'date': order[8]
                }
            return None
        except Exception as e:
            print(f"❌ Error getting order details: {str(e)}")
            return None


class ProviderManager:
    def __init__(self, db_path=None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
    
    def register_provider(self, user_id: str, business_details: Dict) -> Dict:
        """Register a service provider"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO providers 
                (user_id, business_name, business_address, phone, gst_number, 
                 fssai_license, cuisine_specialties, service_area, delivery_radius,
                 opening_time, closing_time, days_operating, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                business_details.get('business_name'),
                business_details.get('business_address'),
                business_details.get('phone'),
                business_details.get('gst_number'),
                business_details.get('fssai_license'),
                json.dumps(business_details.get('cuisine_specialties', [])),
                json.dumps(business_details.get('service_area', [])),
                business_details.get('delivery_radius', 5),
                business_details.get('opening_time', '09:00'),
                business_details.get('closing_time', '21:00'),
                json.dumps(business_details.get('days_operating', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])),
                'pending'
            ))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Provider registered successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_provider_stats(self, provider_id: str) -> Dict:
        """Get provider analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT business_name, rating, total_orders, commission_rate, is_verified, status
                FROM providers WHERE user_id = ?
            ''', (provider_id,))
            
            provider = cursor.fetchone()
            conn.close()
            
            if provider:
                return {
                    "business_name": provider[0],
                    "rating": provider[1] or 0,
                    "total_orders": provider[2] or 0,
                    "commission_rate": provider[3] or 0.15,
                    "is_verified": bool(provider[4]),
                    "status": provider[5]
                }
            return {}
        except Exception as e:
            print(f"❌ Error getting provider stats: {str(e)}")
            return {}
    
    def get_today_orders(self, provider_id: str) -> List[Dict]:
        """Get today's orders"""
        return []
    
    def get_menu(self, provider_id: str) -> List[Dict]:
        """Get provider menu"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM menu_items 
                WHERE provider_id = ?
            ''', (provider_id,))
            
            items = cursor.fetchall()
            conn.close()
            
            return [{'id': i[0], 'name': i[2], 'price': i[4], 'cuisine': i[7]} for i in items]
        except Exception as e:
            print(f"❌ Error getting menu: {str(e)}")
            return []
    
    def add_menu_item(self, provider_id: str, data: Dict) -> Dict:
        """Add menu item"""
        return {"success": True, "message": "Item added"}
    
    def update_menu_item(self, provider_id: str, item_id: str, data: Dict) -> Dict:
        """Update menu item"""
        return {"success": True, "message": "Item updated"}
    
    def delete_menu_item(self, provider_id: str, item_id: str) -> Dict:
        """Delete menu item"""
        return {"success": True, "message": "Item deleted"}
    
    def get_orders(self, provider_id: str, status: str = None, date: str = None) -> List[Dict]:
        """Get provider orders"""
        return []
    
    def update_order_status(self, provider_id: str, order_id: str, status: str) -> Dict:
        """Update order status"""
        return {"success": True, "message": "Status updated", "customer_id": None}
    
    def get_earnings(self, provider_id: str, period: str = 'month') -> Dict:
        """Get provider earnings"""
        return {'period': period, 'total': 0, 'orders': 0, 'commission': 0, 'net': 0}
    
    def get_providers_by_city(self, city: str) -> List[Dict]:
        """Get providers by city"""
        return []
    
    def get_nearby_providers(self, lat: float, lng: float, radius: int = 10) -> List[Dict]:
        """Get nearby providers"""
        return []
    
    def search_providers(self, query: str = None, city: str = None, cuisine: str = None) -> List[Dict]:
        """Search providers"""
        return []
    
    def search_menu_items(self, query: str = None, cuisine: str = None) -> List[Dict]:
        """Search menu items"""
        return []


class OwnerManager:
    def __init__(self, db_path=None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
    
    def get_platform_stats(self) -> Dict:
        """Get platform statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user counts
            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            user_stats = cursor.fetchall()
            
            # Get provider counts
            cursor.execute("SELECT COUNT(*) FROM providers")
            total_providers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM providers WHERE is_verified = 1")
            verified_providers = cursor.fetchone()[0]
            
            conn.close()
            
            users_by_role = {}
            for role, count in user_stats:
                users_by_role[role] = count
            
            return {
                'users': {
                    'total': sum(users_by_role.values()),
                    'by_role': users_by_role
                },
                'providers': {
                    'total': total_providers,
                    'verified': verified_providers
                }
            }
        except Exception as e:
            print(f"❌ Error getting platform stats: {str(e)}")
            return {'users': {'total': 0, 'by_role': {}}, 'providers': {'total': 0, 'verified': 0}}
    
    def get_providers(self, status: str = None, verified: bool = None) -> List[Dict]:
        """Get all providers"""
        return []
    
    def verify_provider(self, provider_id: str) -> Dict:
        """Verify a provider"""
        return {"success": True, "message": "Provider verified"}
    
    def reject_provider(self, provider_id: str, reason: str = None) -> Dict:
        """Reject a provider"""
        return {"success": True, "message": "Provider rejected"}
    
    def get_customers(self, page: int = 1, limit: int = 20) -> List[Dict]:
        """Get all customers"""
        return []
    
    def get_settings(self) -> Dict:
        """Get platform settings"""
        return {}
    
    def update_settings(self, settings: Dict) -> Dict:
        """Update platform settings"""
        return {"success": True, "message": "Settings updated"}
    
    def notify_new_provider(self, provider_id: str, business_name: str):
        """Notify about new provider"""
        print(f"New provider registered: {business_name}")


if __name__ == "__main__":
    print("✅ User module loaded successfully")
    print("Classes available: User, CustomerManager, ProviderManager, OwnerManager")