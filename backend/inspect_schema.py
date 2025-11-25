from sqlalchemy import text
from app.infrastructure.db.session import engine

def inspect_schema():
    with engine.connect() as conn:
        print("Inspecting users table schema...")
        result = conn.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users';"))
        columns = result.fetchall()
        print(f"{'Column':<20} {'Type':<15} {'Nullable'}")
        print("-" * 45)
        for col in columns:
            print(f"{col[0]:<20} {col[1]:<15} {col[2]}")

if __name__ == "__main__":
    inspect_schema()
