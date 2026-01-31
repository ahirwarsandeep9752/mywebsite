from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE FUNCTIONS ----------

def get_db():
    return sqlite3.connect("users.db")

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    db.commit()
    db.close()

# Run this once when app starts
init_db()

# ---------- ROUTES ----------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT password FROM users WHERE username=?",
            (username,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[0], password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("index.html", message="Wrong Username or Password ❌")

    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        db.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------- AI TOOL PAGE ----------

@app.route("/hook")
def hook():
    return render_template("hook.html")


# ---------- RENDER DEPLOYMENT ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
