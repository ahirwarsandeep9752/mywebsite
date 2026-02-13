from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, session
import sqlite3, os, smtplib
from werkzeug.security import check_password_hash, generate_password_hash
from google import genai
from datetime import date
import razorpay
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ===== ENV =====
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# ===== AI =====
client = genai.Client(api_key=GEMINI_KEY)
MODEL_NAME = "models/gemini-flash-latest"

# ===== CONFIG =====
DAILY_LIMIT = 5
PRO_PRICE = 19900

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

# ---------- DATABASE ----------

def get_db():
    return sqlite3.connect("users.db")

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT,
        is_pro INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS usage(
        username TEXT,
        date TEXT,
        count INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payments(
        username TEXT,
        razorpay_id TEXT,
        amount INTEGER,
        date TEXT
    )""")

    db.commit()
    db.close()

init_db()

# ---------- HELPERS ----------

def is_pro_user(username):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT is_pro FROM users WHERE username=?", (username,))
    row = c.fetchone()
    db.close()
    return row and row[0] == 1

def check_and_update_usage(username):
    today = str(date.today())
    db = get_db()
    c = db.cursor()

    c.execute("SELECT count FROM usage WHERE username=? AND date=?", (username,today))
    row = c.fetchone()

    if row:
        if row[0] >= DAILY_LIMIT:
            return False
        c.execute("UPDATE usage SET count=count+1 WHERE username=? AND date=?", (username,today))
    else:
        c.execute("INSERT INTO usage VALUES (?,?,1)", (username,today))

    db.commit()
    db.close()
    return True

def generate_hooks_ai(topic, tone):
    prompt = f"""
Generate 5 {tone} viral hooks for:
{topic}
Under 12 words. Emotional.
"""
    try:
        res = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return res.text
    except:
        return "AI error"

# ---------- EMAIL ----------

def send_contact_email(name, email, message):
    msg = EmailMessage()
    msg["Subject"] = "New Contact Lead"
    msg["From"] = EMAIL_HOST_USER
    msg["To"] = EMAIL_HOST_USER
    msg.set_content(f"""
Name: {name}
Email: {email}
Message: {message}
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        smtp.send_message(msg)

# ---------- AUTH ----------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        db = get_db()
        c = db.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (u,))
        user = c.fetchone()
        db.close()

        if user and check_password_hash(user[0], p):
            session["user"] = u
            return redirect("/dashboard")

    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form.get("username")
        e = request.form.get("email")
        p = generate_password_hash(request.form.get("password"))

        db = get_db()
        c = db.cursor()
        c.execute("INSERT INTO users(username,email,password) VALUES (?,?,?)",(u,e,p))
        db.commit()
        db.close()
        return redirect("/")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", pro=is_pro_user(session["user"]))

# ---------- AI TOOL ----------

@app.route("/hook", methods=["GET","POST"])
def hook():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        if not is_pro_user(session["user"]):
            if not check_and_update_usage(session["user"]):
                return render_template("hook.html", result="Daily limit over")

        topic = request.form.get("topic")
        tone = request.form.get("tone")
        result = generate_hooks_ai(topic, tone)
        return render_template("hook.html", result=result)

    return render_template("hook.html")

# ---------- PAYMENT ----------

@app.route("/upgrade")
def upgrade():
    if "user" not in session:
        return redirect("/")

    order = razorpay_client.order.create({
        "amount": PRO_PRICE,
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template("upgrade.html",
        key=RAZORPAY_KEY_ID,
        amount=PRO_PRICE,
        order_id=order["id"]
    )

@app.route("/payment_success", methods=["POST"])
def payment_success():
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE users SET is_pro=1 WHERE username=?", (session["user"],))
    c.execute("INSERT INTO payments VALUES (?,?,?,?)",
        (session["user"], request.form.get("razorpay_payment_id"), PRO_PRICE, str(date.today())))
    db.commit()
    db.close()
    return "Payment Successful 🎉"

# ---------- CONTACT ----------

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        send_contact_email(
            request.form["name"],
            request.form["email"],
            request.form["message"]
        )
        return "Message sent!"
    return render_template("contact.html")

# ---------- ADMIN ----------
ADMIN_USERNAME = "SANDEEP AHIRWAR"

@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/")

    if session["user"] != ADMIN_USERNAME:
        return "Access Denied: You are not admin"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username,email,is_pro FROM users")
    users = cursor.fetchall()
    db.close()

    return render_template("admin.html", users=users)

# ---------- RUN ----------

if __name__ == "__main__":
    app.run(debug=True)
