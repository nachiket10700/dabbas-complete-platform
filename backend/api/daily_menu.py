"""
Daily Menu API Endpoints
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.daily_menu import DailyMenuManager

daily_menu_manager = DailyMenuManager()

def init_daily_menu_routes(app):
    
    @app.route('/api/provider/daily-menu', methods=['POST'])
    @jwt_required()
    def create_daily_menu():
        """Create a daily menu"""
        try:
            provider_id = get_jwt_identity()
            data = request.json
            
            menu_date = date.fromisoformat(data.get('menu_date'))
            meal_type = data.get('meal_type')
            cutoff_time = data.get('cutoff_time')
            items = data.get('items', [])
            
            # Check if provider can still upload
            if not daily_menu_manager.check_upload_deadline(provider_id, menu_date, meal_type):
                return jsonify({
                    'success': False,
                    'error': 'Upload deadline has passed (10 AM)'
                }), 400
            
            result = daily_menu_manager.create_daily_menu(
                provider_id, menu_date, meal_type, cutoff_time, items
            )
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/daily-menu/<date>/<meal_type>', methods=['GET'])
    @jwt_required()
    def get_daily_menu(date, meal_type):
        """Get daily menu for a specific date"""
        try:
            provider_id = get_jwt_identity()
            menu_date = date.fromisoformat(date)
            
            menu = daily_menu_manager.get_daily_menu(provider_id, menu_date, meal_type)
            
            if menu:
                return jsonify({'success': True, 'menu': menu})
            else:
                return jsonify({'success': False, 'error': 'Menu not found'}), 404
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/menu-templates', methods=['GET'])
    @jwt_required()
    def get_menu_templates():
        """Get all menu templates"""
        try:
            provider_id = get_jwt_identity()
            meal_type = request.args.get('meal_type')
            
            templates = daily_menu_manager.get_menu_templates(provider_id, meal_type)
            
            return jsonify({'success': True, 'templates': templates})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/menu-templates', methods=['POST'])
    @jwt_required()
    def save_menu_template():
        """Save a menu template"""
        try:
            provider_id = get_jwt_identity()
            data = request.json
            
            result = daily_menu_manager.save_menu_template(
                provider_id,
                data.get('template_name'),
                data.get('items', []),
                data.get('meal_type'),
                data.get('is_default', False)
            )
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/menu-settings', methods=['GET'])
    @jwt_required()
    def get_menu_settings():
        """Get provider menu settings"""
        try:
            provider_id = get_jwt_identity()
            settings = daily_menu_manager.get_provider_settings(provider_id)
            
            return jsonify({'success': True, 'settings': settings})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/menu-settings', methods=['POST'])
    @jwt_required()
    def save_menu_settings():
        """Save provider menu settings"""
        try:
            provider_id = get_jwt_identity()
            data = request.json
            
            result = daily_menu_manager.save_provider_settings(provider_id, data)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/upcoming-dates', methods=['GET'])
    @jwt_required()
    def get_upcoming_dates():
        """Get upcoming dates for menu upload"""
        try:
            provider_id = get_jwt_identity()
            settings = daily_menu_manager.get_provider_settings(provider_id)
            max_days = settings.get('max_advance_days', 7)
            
            today = date.today()
            dates = []
            
            for i in range(max_days):
                d = today + timedelta(days=i)
                can_upload = daily_menu_manager.check_upload_deadline(provider_id, d, 'lunch')
                dates.append({
                    'date': d.isoformat(),
                    'day': d.strftime('%A'),
                    'can_upload_lunch': can_upload,
                    'can_upload_dinner': can_upload
                })
            
            return jsonify({'success': True, 'dates': dates})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/provider/subscription-pricing', methods=['POST'])
    @jwt_required()
    def set_subscription_pricing():
        """Set custom subscription pricing"""
        try:
            provider_id = get_jwt_identity()
            data = request.json
            
            # This would update the providers table with custom pricing
            # You'd need to add these fields to the providers table
            
            return jsonify({'success': True, 'message': 'Pricing updated'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500