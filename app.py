from flask import Flask, request, render_template, redirect, url_for, abort, Response
from jinja2 import TemplateNotFound
import os
import sqlite3
import urllib.parse
import requests

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("SECRET_KEY", "dev")

# --- Settings ---
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "254113211652")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "123456")

# --- Fields ---
FIELDS = [
    "client", "phone", "cake_flavour", "size", "colour", "details", "icing",
    "delivery", "date", "time", "location", "writings"
]

DB_FILE = os.getenv("ORDERS_DB", "orders.db")

# --- Database helpers ---
def get_db_connection():
    # Added timeout to avoid "database is locked"
    conn = sqlite3.connect(DB_FILE, timeout=10)
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
        writings TEXT
    )
    """)
    conn.commit()
    conn.close()

# --- WhatsApp helpers ---
def format_order_message(data: dict) -> str:
    lines = ["--- New Cake Order ---"]
    for k in FIELDS:
        label = k.replace("_", " ").title()
        lines.append(f"{label}: {data.get(k, '')}")
    lines.append("----------------------")
    return "\n".join(lines)

def send_whatsapp_if_configured(message_text: str) -> None:
    if not WHATSAPP_PHONE or not WHATSAPP_API_KEY or WHATSAPP_API_KEY == "123456":
        app.logger.info("WhatsApp not sent (missing/placeholder API key).")
        return
    try:
        encoded = urllib.parse.quote_plus(message_text)
        url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={encoded}&apikey={WHATSAPP_API_KEY}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            app.logger.info("WhatsApp message sent.")
        else:
            app.logger.warning(f"WhatsApp API returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        app.logger.exception(f"WhatsApp sending failed: {e}")

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
        send_whatsapp_if_configured(message_text)

        try:
            with get_db_connection() as conn:
                placeholders = ", ".join("?" for _ in FIELDS)
                columns = ", ".join(FIELDS)
                sql = f"INSERT INTO orders ({columns}) VALUES ({placeholders})"
                values = [data[field] for field in FIELDS]
                conn.execute(sql, values)
                conn.commit()
        except Exception as e:
            app.logger.error(f"Error saving order: {e}")
            return f"<h2>Error saving order: {e}</h2>", 500

        return redirect(url_for("thank_you"))

    return render_template("order.html")

@app.route("/thank-you")
def thank_you():
    try:
        return render_template("thank_you.html")
    except TemplateNotFound:
        return "<h2>Thank you! Your order has been received.</h2><p><a href='/'>Back to Home</a></p>"

@app.route("/view-orders")
def view_orders():
    if request.args.get("admin") != "1":
        abort(403)
    with get_db_connection() as conn:
        orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("view_orders.html", orders=orders)

@app.route("/sitemap.xml")
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
