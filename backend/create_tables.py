# create_tables.py
from app import app, db
from models.user import User
from models.provider import Provider
from models.payment import PaymentProcessor
from models.complaint import ComplaintManager

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("✅ All tables created successfully!")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\n📋 Tables in database: {tables}")