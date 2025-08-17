import sqlite3

# Connect to your database
conn = sqlite3.connect("orders.db")
cursor = conn.cursor()

# Drop the old orders table
cursor.execute("DROP TABLE IF EXISTS orders")
conn.commit()
conn.close()

print("✅ Old table deleted. It will be recreated when you run app.py")
