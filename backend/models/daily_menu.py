"""
Daily Menu Management Module
"""

import sqlite3
import json
import os
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional
import secrets

class DailyMenuManager:
    """Manage daily menus for providers"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """Initialize daily menu tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Daily menus table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_menus (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                menu_date DATE NOT NULL,
                meal_type TEXT NOT NULL,  -- 'lunch' or 'dinner'
                upload_deadline TIMESTAMP,
                order_cutoff_time TIME,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES providers(user_id) ON DELETE CASCADE,
                UNIQUE(provider_id, menu_date, meal_type)
            )
        ''')
        
        # Daily menu items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_menu_items (
                id TEXT PRIMARY KEY,
                daily_menu_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                discounted_price REAL,
                category TEXT,
                image_url TEXT,
                is_vegetarian BOOLEAN DEFAULT 0,
                is_vegan BOOLEAN DEFAULT 0,
                is_gluten_free BOOLEAN DEFAULT 0,
                spicy_level TEXT DEFAULT 'medium',
                available_quantity INTEGER DEFAULT 0,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (daily_menu_id) REFERENCES daily_menus(id) ON DELETE CASCADE
            )
        ''')
        
        # Menu templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu_templates (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                template_name TEXT NOT NULL,
                items TEXT,  -- JSON array of menu items
                meal_type TEXT,  -- 'lunch', 'dinner', or 'both'
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES providers(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Provider settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_menu_settings (
                provider_id TEXT PRIMARY KEY,
                lunch_cutoff_time TIME DEFAULT '11:00',
                dinner_cutoff_time TIME DEFAULT '19:00',
                weekly_subscription_discount REAL DEFAULT 10,  -- percentage
                monthly_subscription_discount REAL DEFAULT 20,  -- percentage
                max_advance_days INTEGER DEFAULT 7,
                allow_preorders BOOLEAN DEFAULT 1,
                auto_publish_time TIME DEFAULT '10:00',
                FOREIGN KEY (provider_id) REFERENCES providers(user_id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Daily menu tables initialized")
    
    def create_daily_menu(self, provider_id: str, menu_date: date, meal_type: str, 
                         cutoff_time: str, items: List[Dict]) -> Dict:
        """Create a daily menu"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if menu already exists for this date
            cursor.execute('''
                SELECT id FROM daily_menus 
                WHERE provider_id = ? AND menu_date = ? AND meal_type = ?
            ''', (provider_id, menu_date.isoformat(), meal_type))
            
            if cursor.fetchone():
                return {'success': False, 'error': 'Menu already exists for this date'}
            
            # Set upload deadline (10 AM on the menu date)
            upload_deadline = datetime.combine(menu_date, time(10, 0))
            
            # Create menu
            menu_id = f"DM{secrets.token_hex(4).upper()}"
            cursor.execute('''
                INSERT INTO daily_menus 
                (id, provider_id, menu_date, meal_type, upload_deadline, order_cutoff_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (menu_id, provider_id, menu_date.isoformat(), meal_type, 
                  upload_deadline, cutoff_time))
            
            # Add menu items
            for item in items:
                item_id = f"DMI{secrets.token_hex(4).upper()}"
                cursor.execute('''
                    INSERT INTO daily_menu_items 
                    (id, daily_menu_id, name, description, price, discounted_price,
                     category, image_url, is_vegetarian, is_vegan, is_gluten_free,
                     spicy_level, available_quantity, is_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item_id, menu_id,
                    item.get('name'),
                    item.get('description'),
                    item.get('price'),
                    item.get('discounted_price'),
                    item.get('category'),
                    item.get('image_url'),
                    1 if item.get('is_vegetarian') else 0,
                    1 if item.get('is_vegan') else 0,
                    1 if item.get('is_gluten_free') else 0,
                    item.get('spicy_level', 'medium'),
                    item.get('available_quantity', 0),
                    1 if item.get('is_available', True) else 0
                ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'menu_id': menu_id}
            
        except Exception as e:
            print(f"Error creating daily menu: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_daily_menu(self, provider_id: str, menu_date: date, meal_type: str) -> Optional[Dict]:
        """Get daily menu for a specific date"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM daily_menus 
                WHERE provider_id = ? AND menu_date = ? AND meal_type = ?
            ''', (provider_id, menu_date.isoformat(), meal_type))
            
            menu = cursor.fetchone()
            if not menu:
                conn.close()
                return None
            
            # Get menu items
            cursor.execute('''
                SELECT * FROM daily_menu_items WHERE daily_menu_id = ?
            ''', (menu[0],))
            
            items = cursor.fetchall()
            conn.close()
            
            return {
                'id': menu[0],
                'provider_id': menu[1],
                'menu_date': menu[2],
                'meal_type': menu[3],
                'upload_deadline': menu[4],
                'cutoff_time': menu[5],
                'is_active': bool(menu[6]),
                'items': [{
                    'id': i[0],
                    'name': i[2],
                    'description': i[3],
                    'price': i[4],
                    'discounted_price': i[5],
                    'category': i[6],
                    'image_url': i[7],
                    'is_vegetarian': bool(i[8]),
                    'is_vegan': bool(i[9]),
                    'is_gluten_free': bool(i[10]),
                    'spicy_level': i[11],
                    'available_quantity': i[12],
                    'is_available': bool(i[13])
                } for i in items]
            }
            
        except Exception as e:
            print(f"Error getting daily menu: {str(e)}")
            return None
    
    def save_menu_template(self, provider_id: str, template_name: str, 
                          items: List[Dict], meal_type: str, is_default: bool = False) -> Dict:
        """Save a menu template for quick reuse"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # If this is default, remove default from other templates
            if is_default:
                cursor.execute('''
                    UPDATE menu_templates SET is_default = 0 
                    WHERE provider_id = ? AND meal_type = ?
                ''', (provider_id, meal_type))
            
            template_id = f"TMP{secrets.token_hex(4).upper()}"
            cursor.execute('''
                INSERT INTO menu_templates 
                (id, provider_id, template_name, items, meal_type, is_default)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (template_id, provider_id, template_name, 
                  json.dumps(items), meal_type, 1 if is_default else 0))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'template_id': template_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_menu_templates(self, provider_id: str, meal_type: str = None) -> List[Dict]:
        """Get all menu templates for a provider"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if meal_type:
                cursor.execute('''
                    SELECT * FROM menu_templates 
                    WHERE provider_id = ? AND (meal_type = ? OR meal_type = 'both')
                    ORDER BY is_default DESC, created_at DESC
                ''', (provider_id, meal_type))
            else:
                cursor.execute('''
                    SELECT * FROM menu_templates 
                    WHERE provider_id = ?
                    ORDER BY is_default DESC, created_at DESC
                ''', (provider_id,))
            
            templates = cursor.fetchall()
            conn.close()
            
            return [{
                'id': t[0],
                'name': t[2],
                'items': json.loads(t[3]),
                'meal_type': t[4],
                'is_default': bool(t[5])
            } for t in templates]
            
        except Exception as e:
            print(f"Error getting templates: {str(e)}")
            return []
    
    def save_provider_settings(self, provider_id: str, settings: Dict) -> Dict:
        """Save provider menu settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO provider_menu_settings 
                (provider_id, lunch_cutoff_time, dinner_cutoff_time, 
                 weekly_subscription_discount, monthly_subscription_discount,
                 max_advance_days, allow_preorders, auto_publish_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                provider_id,
                settings.get('lunch_cutoff', '11:00'),
                settings.get('dinner_cutoff', '19:00'),
                settings.get('weekly_discount', 10),
                settings.get('monthly_discount', 20),
                settings.get('max_advance_days', 7),
                1 if settings.get('allow_preorders', True) else 0,
                settings.get('auto_publish', '10:00')
            ))
            
            conn.commit()
            conn.close()
            
            return {'success': True, 'message': 'Settings saved'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_provider_settings(self, provider_id: str) -> Dict:
        """Get provider menu settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM provider_menu_settings WHERE provider_id = ?', (provider_id,))
            settings = cursor.fetchone()
            conn.close()
            
            if settings:
                return {
                    'lunch_cutoff': settings[1],
                    'dinner_cutoff': settings[2],
                    'weekly_discount': settings[3],
                    'monthly_discount': settings[4],
                    'max_advance_days': settings[5],
                    'allow_preorders': bool(settings[6]),
                    'auto_publish': settings[7]
                }
            return {}
            
        except Exception as e:
            print(f"Error getting settings: {str(e)}")
            return {}
    
    def check_upload_deadline(self, provider_id: str, menu_date: date, meal_type: str) -> bool:
        """Check if provider can still upload menu for given date"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT upload_deadline FROM daily_menus 
                WHERE provider_id = ? AND menu_date = ? AND meal_type = ?
            ''', (provider_id, menu_date.isoformat(), meal_type))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                deadline = datetime.fromisoformat(result[0])
                return datetime.now() <= deadline
            return True  # No menu yet, can upload
            
        except Exception as e:
            print(f"Error checking deadline: {str(e)}")
            return False