import sqlite3

def add_custom_prompt_column():
    db_path = "c:/programming/company-buddy/backend/company_buddy.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE tenants ADD COLUMN custom_prompt TEXT")
        conn.commit()
        print("Column 'custom_prompt' added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'custom_prompt' already exists.")
        else:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_custom_prompt_column()
