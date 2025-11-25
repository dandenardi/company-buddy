from sqlalchemy import text
from app.infrastructure.db.session import engine

def fix_db():
    with engine.connect() as conn:
        print("Adding created_at column to users table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT NOW();"))
            conn.commit()
            print("Successfully added created_at column.")
        except Exception as e:
            print(f"Error (maybe column already exists?): {e}")

if __name__ == "__main__":
    fix_db()
