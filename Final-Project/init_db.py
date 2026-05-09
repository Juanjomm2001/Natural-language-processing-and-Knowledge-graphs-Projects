import sqlite3
import os

def init_inventory_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/inventory.db")
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        origin TEXT,
        price_per_kg REAL,
        stock_kg INTEGER
    )
    ''')
    
    cursor.execute('DELETE FROM inventory')
    
    fruits = [
        ("Melon", "Tomelloso, Spain", 5.50, 150),
        ("Honey", "Munera, Spain", 12.00, 45),
        ("Tomato", "Almeria, Spain", 3.20, 300),
        ("Apple", "Lleida, Spain", 2.10, 500),
        ("Orange", "Valencia, Spain", 1.80, 800),
        ("Watermelon", "Murcia, Spain", 4.00, 200)
    ]
    
    cursor.executemany('''
    INSERT INTO inventory (product_name, origin, price_per_kg, stock_kg)
    VALUES (?, ?, ?, ?)
    ''', fruits)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_inventory_db()
