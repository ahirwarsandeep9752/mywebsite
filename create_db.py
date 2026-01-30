import sqlite3
from werkzeug.security import generate_password_hash

db = sqlite3.connect("users.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")

hashed_password = generate_password_hash("1234")

cursor.execute(
    "INSERT INTO users (username, password) VALUES (?, ?)",
    ("admin", hashed_password)
)

db.commit()
db.close()

print("Secure database created")
