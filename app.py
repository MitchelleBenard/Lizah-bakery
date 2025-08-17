from flask import Flask, request, render_template, redirect, url_for, abort
from jinja2 import TemplateNotFound
import os
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import requests
import sqlite3  # database

# --- Optional .env support ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("SECRET_KEY", "dev")

# --- Settings ---
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "254113211652")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "123456")

FIELDS = [
    "client", "phone", "cake_flavour", "size", "colour", "details", "icing",
    "delivery", "date", "time", "location", "writings",
    "amount", "deposit"
]

# --- Database helper ---
DB_FILE = "orders.db"  # use your actual DB

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client TEXT NOT NULL,
        phone TEXT NOT NULL,
        cake_flavour TEXT NOT NULL,
        size TEXT NOT NULL,
        colour TEXT,
        details TEXT,
        icing TEXT,
        delivery TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        location TEXT,
        writings TEXT,
        amount REAL NOT NULL,
        deposit REAL
    )
    """)
    conn.commit()
    conn.close()

# --- Email & WhatsApp helpers ---
def format_order_message(data: dict) -> str:
    lines = ["--- New Cake Order ---"]
    for k in FIELDS:
        label = k.replace("_", " ").title()
        lines.append(f"{label}: {data.get(k, '')}")
    lines.append("----------------------")
    return "\n".join(lines)

def send_email_if_configured(message_text: str) -> None:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD or EMAIL_PASSWORD == "YOUR_APP_PASSWORD":
        print("ℹ️ Email not sent (missing EMAIL_PASSWORD or using placeholder).")
        return
    msg = MIMEText(message_text)
    msg["Subject"] = "New Cake Order - ENM Kitchen"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

def send_whatsapp_if_configured(message_text: str) -> None:
    if not WHATSAPP_PHONE or not WHATSAPP_API_KEY or WHATSAPP_API_KEY == "123456":
        print("ℹ️ WhatsApp not sent (missing/placeholder API key).")
        return
    try:
        encoded = urllib.parse.quote_plus(message_text)
        url = (
            "https://api.callmebot.com/whatsapp.php"
            f"?phone={WHATSAPP_PHONE}&text={encoded}&apikey={WHATSAPP_API_KEY}"
        )
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            print("✅ WhatsApp message sent.")
        else:
            print(f"❌ WhatsApp API returned status {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"❌ WhatsApp sending failed: {e}")

# --- Routes ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/our-cakes")
def our_cakes():
    return render_template("our-cakes.html")

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        data = {field: request.form.get(field, "") for field in FIELDS}
        message_text = format_order_message(data)
        
        # Send WhatsApp
       # send_email_if_configured(message_text)
        send_whatsapp_if_configured(message_text)
        
        # Save to database
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO orders (
                client, phone, cake_flavour, size, colour, details, icing,
                delivery, date, time, location, writings,
                amount, deposit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [data[field] for field in FIELDS])
        conn.commit()
        conn.close()
        
        return redirect(url_for("thank_you"))
    return render_template("order.html")

@app.route("/thank-you")
def thank_you():
    try:
        return render_template("thank_you.html")
    except TemplateNotFound:
        return (
            "<h2>Thank you! Your order has been received.</h2>"
            "<p><a href='/'>Back to Home</a> | <a href='/order'>Place another order</a></p>"
        )

# --- Admin-only view orders page ---
@app.route("/view-orders")
def view_orders():
    if request.args.get("admin") != "1":
        abort(403)  # Forbidden
    
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return render_template("view_orders.html", orders=orders)
from flask import Response

# --- Sitemap route ---
@app.route("/sitemap.xml", methods=["GET"])
def sitemap():
    try:
        with open("sitemap.xml", "r", encoding="utf-8") as f:
            sitemap_xml = f.read()
        return Response(sitemap_xml, mimetype="application/xml")
    except FileNotFoundError:
        return Response("<urlset></urlset>", mimetype="application/xml")


# --- Run App ---
if __name__ == "__main__":
    init_db()
    print("🚀 ENM Kitchen app running...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)













