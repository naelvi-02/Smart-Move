"""
Database migration script to add NSFW research columns.
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('smart_move.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(models)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    # Add missing columns
    if 'is_vlm' not in existing_cols:
        cursor.execute('ALTER TABLE models ADD COLUMN is_vlm INTEGER DEFAULT 0')
        print("Added is_vlm column")
    
    if 'nsfw_score' not in existing_cols:
        cursor.execute('ALTER TABLE models ADD COLUMN nsfw_score REAL')
        print("Added nsfw_score column")
    
    if 'indonesian_score' not in existing_cols:
        cursor.execute('ALTER TABLE models ADD COLUMN indonesian_score REAL')
        print("Added indonesian_score column")
    
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
