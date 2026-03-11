"""
Database connection module for Dabba's
"""

import os
import sqlite3
from datetime import datetime

class Database:
    """Handle database connections"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(backend_dir, 'database', 'dabbas.db')
        else:
            self.db_path = db_path
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        conn.commit()
        conn.close()
        
        return results
    
    def execute_insert(self, query, params=None):
        """Execute an insert query and return last row id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return last_id

# Create a global database instance
db = Database()