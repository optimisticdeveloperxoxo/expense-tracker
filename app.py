"""
SpendSense - Personal Expense Tracker
Full-stack Flask + SQLite with user auth, per-user data, UPI SMS parser,
Bank Statement upload (PDF + CSV), Themes, Total Expenditure, Forgot Password (OTP)
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, session)
import sqlite3, os, hashlib, re, random, string
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "spendsense_secret_key_2024_pbl"
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
CATEGORIES = ["Food", "Travel", "Shopping", "Entertainment", "Health", "Education", "Others"]

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        source TEXT DEFAULT 'manual',
        date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        month TEXT NOT NULL,
        amount REAL NOT NULL,
        UNIQUE(user_id, month))""")
    c.execute("""CREATE TABLE IF NOT EXISTS otp_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def require_login():
    return session.get("user_id")

def get_current_month():
    return date.today().strftime("%Y-%m")

# ── Auth ──────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","").strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if not user or user["password"] != hash_pw(password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session["user_id"]    = user["id"]
        session["user_name"]  = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}! 👋", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name     = request.form.get("name","").strip()
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","").strip()
        errors = []
        if not name:                      errors.append("Name is required.")
        if not email or "@" not in email: errors.append("Valid email required.")
        if len(password) < 6:             errors.append("Password must be at least 6 characters.")
        if errors:
            for e in errors: flash(e, "error")
            return render_template("signup.html", form_data=request.form)
        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            conn.close()
            flash("An account with this email already exists.", "error")
            return render_template("signup.html", form_data=request.form)
        conn.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                     (name, email, hash_pw(password)))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        session["user_id"]    = user["id"]
        session["user_name"]  = user["name"]
        session["user_email"] = user["email"]
        flash(f"Account created! Welcome, {name} 🎉", "success")
        return redirect(url_for("dashboard"))
    return render_template("signup.html", form_data={})

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ── Forgot Password (OTP) ─────────────────────
@app.route("/forgot_password", methods=["GET","POST"])
def forgot_password():
    if request.method == "POST":
        step = request.form.get("step","email")
        if step == "email":
            email = request.form.get("email","").strip().lower()
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user:
                conn.close()
                flash("No account found with that email.", "error")
                return render_template("forgot_password.html", step="email")
            otp = ''.join(random.choices(string.digits, k=6))
            conn.execute("DELETE FROM otp_store WHERE email=?", (email,))
            conn.execute("INSERT INTO otp_store (email, otp) VALUES (?,?)", (email, otp))
            conn.commit()
            conn.close()
            session["fp_email"] = email
            # In production send OTP via email/SMS. For demo we flash it:
            flash(f"OTP sent! (Demo OTP: {otp}) — In production this would be emailed.", "info")
            return render_template("forgot_password.html", step="otp", email=email)

        elif step == "otp":
            email = request.form.get("email","").strip().lower()
            otp_input = request.form.get("otp","").strip()
            conn = get_db()
            record = conn.execute(
                "SELECT * FROM otp_store WHERE email=? ORDER BY created_at DESC LIMIT 1",
                (email,)).fetchone()
            if not record or record["otp"] != otp_input:
                conn.close()
                flash("Invalid or expired OTP. Please try again.", "error")
                return render_template("forgot_password.html", step="otp", email=email)
            conn.execute("DELETE FROM otp_store WHERE email=?", (email,))
            conn.commit()
            conn.close()
            session["fp_verified"] = email
            return render_template("forgot_password.html", step="reset", email=email)

        elif step == "reset":
            email = request.form.get("email","").strip().lower()
            if session.get("fp_verified") != email:
                flash("Session expired. Please start again.", "error")
                return redirect(url_for("forgot_password"))
            new_pw = request.form.get("new_password","").strip()
            confirm_pw = request.form.get("confirm_password","").strip()
            if len(new_pw) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("forgot_password.html", step="reset", email=email)
            if new_pw != confirm_pw:
                flash("Passwords do not match.", "error")
                return render_template("forgot_password.html", step="reset", email=email)
            conn = get_db()
            conn.execute("UPDATE users SET password=? WHERE email=?", (hash_pw(new_pw), email))
            conn.commit()
            conn.close()
            session.pop("fp_verified", None)
            session.pop("fp_email", None)
            flash("Password reset successfully! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("forgot_password.html", step="email")

# ── Dashboard ─────────────────────────────────
@app.route("/")
def dashboard():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    selected_month    = request.args.get("month", get_current_month())
    selected_category = request.args.get("category","")
    query  = "SELECT * FROM expenses WHERE user_id=? AND strftime('%Y-%m',date)=?"
    params = [uid, selected_month]
    if selected_category:
        query += " AND category=?"; params.append(selected_category)
    query += " ORDER BY date DESC, created_at DESC"
    expenses = conn.execute(query, params).fetchall()
    total_this_month = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND strftime('%Y-%m',date)=?",
        (uid, selected_month)).fetchone()["t"]
    cat_rows = conn.execute(
        """SELECT category, SUM(amount) as total FROM expenses
           WHERE user_id=? AND strftime('%Y-%m',date)=?
           GROUP BY category ORDER BY total DESC""", (uid, selected_month)).fetchall()
    category_totals = [{"category":r["category"],"total":r["total"]} for r in cat_rows]
    budget_row = conn.execute(
        "SELECT amount FROM budgets WHERE user_id=? AND month=?", (uid, selected_month)).fetchone()
    budget          = budget_row["amount"] if budget_row else None
    budget_exceeded = budget and total_this_month > budget
    conn.close()
    return render_template("index.html",
        expenses=expenses, total_this_month=total_this_month,
        category_totals=category_totals, categories=CATEGORIES,
        selected_month=selected_month, selected_category=selected_category,
        budget=budget, budget_exceeded=budget_exceeded, current_month=get_current_month())

# ── Add / Edit / Delete ───────────────────────
@app.route("/add", methods=["GET","POST"])
def add_expense():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    if request.method == "POST":
        amount       = request.form.get("amount","").strip()
        category     = request.form.get("category","").strip()
        description  = request.form.get("description","").strip()
        expense_date = request.form.get("date","").strip()
        errors = []
        try:
            amount = float(amount)
            if amount <= 0: raise ValueError
        except (ValueError, TypeError): errors.append("Enter a valid amount greater than zero.")
        if category not in CATEGORIES: errors.append("Select a valid category.")
        if not expense_date:            errors.append("Date is required.")
        if errors:
            for e in errors: flash(e,"error")
            return render_template("add.html", categories=CATEGORIES, form_data=request.form)
        conn = get_db()
        conn.execute("INSERT INTO expenses (user_id,amount,category,description,date,source) VALUES (?,?,?,?,?,?)",
                     (uid, amount, category, description, expense_date, "manual"))
        conn.commit(); conn.close()
        flash("Expense added! 🎉","success")
        return redirect(url_for("dashboard"))
    return render_template("add.html", categories=CATEGORIES, form_data={"date":date.today().isoformat()})

@app.route("/edit/<int:expense_id>", methods=["GET","POST"])
def edit_expense(expense_id):
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    expense = conn.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (expense_id,uid)).fetchone()
    if not expense:
        conn.close(); flash("Expense not found.","error"); return redirect(url_for("dashboard"))
    if request.method == "POST":
        amount       = request.form.get("amount","").strip()
        category     = request.form.get("category","").strip()
        description  = request.form.get("description","").strip()
        expense_date = request.form.get("date","").strip()
        errors = []
        try:
            amount = float(amount)
            if amount <= 0: raise ValueError
        except (ValueError,TypeError): errors.append("Enter a valid amount.")
        if category not in CATEGORIES: errors.append("Select a valid category.")
        if not expense_date:            errors.append("Date is required.")
        if errors:
            for e in errors: flash(e,"error")
            conn.close()
            return render_template("edit.html", expense=expense, categories=CATEGORIES)
        conn.execute("UPDATE expenses SET amount=?,category=?,description=?,date=? WHERE id=? AND user_id=?",
                     (amount,category,description,expense_date,expense_id,uid))
        conn.commit(); conn.close()
        flash("Expense updated! ✅","success")
        return redirect(url_for("dashboard"))
    conn.close()
    return render_template("edit.html", expense=expense, categories=CATEGORIES)

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id,uid))
    conn.commit(); conn.close()
    flash("Expense deleted. 🗑️","info")
    return redirect(url_for("dashboard"))

# ── Budget ────────────────────────────────────
@app.route("/set_budget", methods=["POST"])
def set_budget():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    month  = request.form.get("month", get_current_month())
    amount = request.form.get("budget_amount","").strip()
    try:
        amount = float(amount)
        if amount <= 0: raise ValueError
    except (ValueError,TypeError):
        flash("Enter a valid budget amount.","error")
        return redirect(url_for("dashboard"))
    conn = get_db()
    conn.execute("""INSERT INTO budgets (user_id,month,amount) VALUES (?,?,?)
        ON CONFLICT(user_id,month) DO UPDATE SET amount=excluded.amount""",
        (uid, month, amount))
    conn.commit(); conn.close()
    flash(f"Budget set to ₹{amount:,.0f} for {month}! 💰","success")
    return redirect(url_for("dashboard"))

# ── Chart API ─────────────────────────────────
@app.route("/api/chart_data")
def chart_data():
    uid = require_login()
    if not uid: return jsonify({"labels":[],"values":[]})
    month = request.args.get("month", get_current_month())
    conn  = get_db()
    rows  = conn.execute(
        """SELECT category, SUM(amount) as total FROM expenses
           WHERE user_id=? AND strftime('%Y-%m',date)=?
           GROUP BY category ORDER BY total DESC""", (uid,month)).fetchall()
    conn.close()
    return jsonify({"labels":[r["category"] for r in rows],"values":[r["total"] for r in rows]})

# ── UPI Tracker ───────────────────────────────
@app.route("/upi")
def upi_tracker():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    upi_expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id=? AND source='upi' ORDER BY date DESC, created_at DESC",
        (uid,)).fetchall()
    upi_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND source='upi'",
        (uid,)).fetchone()["t"]
    month_total = conn.execute(
        """SELECT COALESCE(SUM(amount),0) as t FROM expenses
           WHERE user_id=? AND source='upi' AND strftime('%Y-%m',date)=?""",
        (uid, get_current_month())).fetchone()["t"]
    conn.close()
    return render_template("upi.html",
        upi_expenses=upi_expenses, upi_total=upi_total,
        month_total=month_total, categories=CATEGORIES,
        current_month=get_current_month())

@app.route("/upi/parse_sms", methods=["POST"])
def parse_sms():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    sms_text       = request.form.get("sms_text","").strip()
    default_cat    = request.form.get("category","Others").strip()
    default_date   = request.form.get("parse_date", date.today().isoformat()).strip()
    if not sms_text:
        flash("Paste at least one SMS message.","error")
        return redirect(url_for("upi_tracker"))

    blocks = [b.strip() for b in re.split(r'\n{2,}', sms_text) if b.strip()]
    if len(blocks) == 1:
        blocks = [sms_text.strip()]

    parsed = []
    failed = []
    for block in blocks:
        r = parse_single_sms(block, default_cat, default_date)
        if r:
            parsed.append(r)
        else:
            failed.append(block[:70])

    if not parsed:
        flash("Could not read any transaction. Check the SMS format below for help.","error")
        return redirect(url_for("upi_tracker"))

    conn = get_db()
    for t in parsed:
        conn.execute(
            "INSERT INTO expenses (user_id,amount,category,description,date,source) VALUES (?,?,?,?,?,?)",
            (uid, t["amount"], t["category"], t["description"], t["date"], "upi"))
    conn.commit(); conn.close()
    msg = f"✅ Imported {len(parsed)} UPI transaction(s)!"
    if failed: msg += f" ({len(failed)} line(s) skipped — unrecognised format.)"
    flash(msg,"success")
    return redirect(url_for("upi_tracker"))

@app.route("/upi/delete/<int:expense_id>", methods=["POST"])
def delete_upi(expense_id):
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=? AND source='upi'",(expense_id,uid))
    conn.commit(); conn.close()
    flash("UPI transaction removed.","info")
    return redirect(url_for("upi_tracker"))

# ── Bank Statement ────────────────────────────
@app.route("/bank_statement")
def bank_statement():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    bank_expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id=? AND source='bank' ORDER BY date DESC, created_at DESC",
        (uid,)).fetchall()
    bank_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND source='bank'",
        (uid,)).fetchone()["t"]
    month_total = conn.execute(
        """SELECT COALESCE(SUM(amount),0) as t FROM expenses
           WHERE user_id=? AND source='bank' AND strftime('%Y-%m',date)=?""",
        (uid, get_current_month())).fetchone()["t"]
    conn.close()
    return render_template("bank_statement.html",
        bank_expenses=bank_expenses, bank_total=bank_total,
        month_total=month_total, categories=CATEGORIES,
        current_month=get_current_month())

@app.route("/bank_statement/upload", methods=["POST"])
def upload_bank_statement():
    uid = require_login()
    if not uid: return redirect(url_for("login"))

    file = request.files.get("statement_file")
    default_cat = request.form.get("category","Others").strip()

    if not file or file.filename == "":
        flash("Please select a file to upload.","error")
        return redirect(url_for("bank_statement"))

    filename = file.filename.lower()
    transactions = []

    if filename.endswith(".pdf"):
        transactions = parse_bank_pdf(file, default_cat)
    elif filename.endswith(".csv"):
        transactions = parse_bank_csv(file, default_cat)
    else:
        flash("Unsupported file type. Please upload a PDF or CSV bank statement.","error")
        return redirect(url_for("bank_statement"))

    if not transactions:
        flash("No debit transactions found in the uploaded statement. Try a different file or format.","error")
        return redirect(url_for("bank_statement"))

    conn = get_db()
    for t in transactions:
        conn.execute(
            "INSERT INTO expenses (user_id,amount,category,description,date,source) VALUES (?,?,?,?,?,?)",
            (uid, t["amount"], t["category"], t["description"], t["date"], "bank"))
    conn.commit(); conn.close()
    flash(f"✅ Imported {len(transactions)} transaction(s) from your bank statement!","success")
    return redirect(url_for("bank_statement"))

@app.route("/bank_statement/delete/<int:expense_id>", methods=["POST"])
def delete_bank(expense_id):
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=? AND source='bank'",(expense_id,uid))
    conn.commit(); conn.close()
    flash("Bank transaction removed.","info")
    return redirect(url_for("bank_statement"))

def parse_bank_pdf(file, default_cat):
    """Parse bank statement PDF and extract debit transactions."""
    import io
    try:
        import pdfplumber
        transactions = []
        data = file.read()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
                # Also try table extraction
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            row_text = " | ".join([str(c) for c in row if c])
                            parsed = parse_bank_row_text(row_text, default_cat)
                            if parsed:
                                transactions.append(parsed)

            # Parse text lines if table parsing gave nothing
            if not transactions:
                for line in full_text.split("\n"):
                    parsed = parse_bank_row_text(line, default_cat)
                    if parsed:
                        transactions.append(parsed)

        return transactions
    except Exception as e:
        return []

def parse_bank_csv(file, default_cat):
    """Parse CSV bank statement."""
    import io, csv
    transactions = []
    try:
        content = file.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            # Try common column names
            amount = None
            desc = ""
            txn_date = date.today().isoformat()

            for key in row:
                kl = key.lower().strip()
                val = str(row[key]).strip()

                if kl in ["debit","withdrawal","dr","debit amount","amount","withdrawal amount"]:
                    try:
                        v = float(val.replace(",","").replace("₹","").replace("Rs","").strip())
                        if v > 0: amount = v
                    except: pass

                if kl in ["description","narration","particulars","details","transaction details","remarks","info"]:
                    desc = val

                if kl in ["date","transaction date","txn date","value date","posting date"]:
                    txn_date = parse_date_string(val) or txn_date

            if amount:
                cat = auto_categorise(desc) or default_cat
                transactions.append({
                    "amount": amount,
                    "category": cat,
                    "description": (f"Bank: {desc}"[:200] if desc else "Bank Transaction"),
                    "date": txn_date
                })
    except Exception:
        pass
    return transactions

def parse_bank_row_text(text, default_cat):
    """Try to extract a debit transaction from a text line/row."""
    tl = text.lower()
    debit_kw = ["dr","debit","withdrawal","paid","purchase","pos","atm","neft","rtgs","imps","upi","bill payment"]
    credit_kw = ["cr","credit","deposit","interest","refund","cashback","received"]

    is_credit = any(k in tl for k in credit_kw)
    is_debit = any(k in tl for k in debit_kw)
    if is_credit and not is_debit: return None

    # Find amount
    amount = None
    for pat in [
        r'(?:dr|debit)[^\d]*([0-9,]+(?:\.[0-9]{1,2})?)',
        r'(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        r'([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:dr|debit)',
        r'\|\s*([0-9,]+\.[0-9]{2})\s*\|',
    ]:
        m = re.search(pat, tl)
        if m:
            try:
                v = float(m.group(1).replace(",",""))
                if v > 0: amount = v; break
            except: pass

    if not amount: return None
    if amount < 1: return None  # skip tiny amounts like 0.00

    # Find date
    txn_date = parse_date_string(text) or date.today().isoformat()

    # Description: use full text truncated
    desc = re.sub(r'\s+', ' ', text).strip()[:150]
    cat = auto_categorise(desc) or default_cat

    return {
        "amount": amount,
        "category": cat,
        "description": f"Bank: {desc}",
        "date": txn_date
    }

def parse_date_string(text):
    """Try to extract a date from a string."""
    months_map = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
                  "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
    patterns = [
        (r'(\d{2})[\/\-](\d{2})[\/\-](\d{4})', lambda g: f"{g[2]}-{g[1].zfill(2)}-{g[0].zfill(2)}"),
        (r'(\d{4})[\/\-](\d{2})[\/\-](\d{2})', lambda g: f"{g[0]}-{g[1].zfill(2)}-{g[2].zfill(2)}"),
        (r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})', lambda g: f"20{g[2]}-{g[1].zfill(2)}-{g[0].zfill(2)}"),
        (r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', lambda g: f"{g[2]}-{months_map.get(g[1].lower()[:3],'01')}-{g[0].zfill(2)}"),
        (r'(\d{1,2})-([A-Za-z]{3})-(\d{4})', lambda g: f"{g[2]}-{months_map.get(g[1].lower()[:3],'01')}-{g[0].zfill(2)}"),
        (r'(\d{1,2})([A-Za-z]{3})(\d{2,4})', lambda g: f"{'20'+g[2] if len(g[2])==2 else g[2]}-{months_map.get(g[1].lower()[:3],'01')}-{g[0].zfill(2)}"),
    ]
    for pat, formatter in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                result = formatter(m.groups())
                datetime.strptime(result, "%Y-%m-%d")
                return result
            except: pass
    return None

# ── Total Expenditure ─────────────────────────
@app.route("/total_expenditure")
def total_expenditure():
    uid = require_login()
    if not uid: return redirect(url_for("login"))
    conn = get_db()
    selected_month = request.args.get("month", get_current_month())

    upi_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND source='upi' AND strftime('%Y-%m',date)=?",
        (uid, selected_month)).fetchone()["t"]
    bank_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND source='bank' AND strftime('%Y-%m',date)=?",
        (uid, selected_month)).fetchone()["t"]
    manual_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE user_id=? AND source='manual' AND strftime('%Y-%m',date)=?",
        (uid, selected_month)).fetchone()["t"]

    grand_total = upi_total + bank_total + manual_total

    cat_rows = conn.execute(
        """SELECT category, SUM(amount) as total FROM expenses
           WHERE user_id=? AND strftime('%Y-%m',date)=?
           GROUP BY category ORDER BY total DESC""", (uid, selected_month)).fetchall()
    category_totals = [{"category":r["category"],"total":r["total"]} for r in cat_rows]

    # Monthly breakdown (last 6 months)
    monthly_rows = conn.execute(
        """SELECT strftime('%Y-%m',date) as month, SUM(amount) as total
           FROM expenses WHERE user_id=?
           GROUP BY strftime('%Y-%m',date)
           ORDER BY month DESC LIMIT 6""", (uid,)).fetchall()
    monthly_data = [{"month":r["month"],"total":r["total"]} for r in monthly_rows]

    conn.close()
    return render_template("total_expenditure.html",
        upi_total=upi_total, bank_total=bank_total, manual_total=manual_total,
        grand_total=grand_total, category_totals=category_totals,
        monthly_data=monthly_data, selected_month=selected_month,
        current_month=get_current_month())

# ── SMS Parser logic ──────────────────────────
def parse_single_sms(text, default_category="Others", default_date=None):
    tl = text.lower()
    debit_kw  = ["debited","debit","paid","sent","transferred","payment of","spent",
                 "withdrawn","purchase","txn of","upi","rs.","inr"]
    credit_kw = ["credited","received","credit","deposited","refund","cashback"]
    is_credit = any(k in tl for k in credit_kw)
    is_debit  = any(k in tl for k in debit_kw)
    if is_credit and not is_debit: return None
    if not is_debit:               return None

    amount = None
    for pat in [
        r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)',
        r'([\d,]+(?:\.\d{1,2})?)\s*(?:rs\.?|inr|₹)',
        r'amount\s*(?:of|:)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
        r'debited\s+(?:by|with|for)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
        r'paid\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
        r'txn\s+of\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
    ]:
        m = re.search(pat, tl)
        if m:
            try:
                v = float(m.group(1).replace(",",""))
                if v > 0: amount = v; break
            except ValueError: pass
    if not amount: return None

    merchant = ""
    for pat in [
        r'(?:to|at|paid to|sent to|merchant|vpa)\s+([A-Za-z0-9@._\-\s]{3,40}?)(?:\s+(?:on|via|ref|upi|for)|$)',
        r'(?:using upi at|purchase at)\s+([A-Za-z0-9\s]{3,35})',
        r'(?:info:|narration:|remarks?:)\s*([A-Za-z0-9@.\-\s]{3,50})',
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            merchant = m.group(1).strip().rstrip(".")
            if len(merchant) >= 3: break

    txn_date = default_date or date.today().isoformat()
    months_map = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
                  "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
    for pat in [
        r'(\d{2})[\/\-](\d{2})[\/\-](\d{4})',
        r'(\d{4})[\/\-](\d{2})[\/\-](\d{2})',
        r'(\d{2})[\/\-](\d{2})[\/\-](\d{2})',
        r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})',
        r'([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{4})',
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            g = m.groups()
            try:
                if len(g[0])==4:
                    txn_date = f"{g[0]}-{g[1].zfill(2)}-{g[2].zfill(2)}"
                elif g[1].isalpha():
                    mo = months_map.get(g[1].lower()[:3])
                    if mo: txn_date = f"{g[2]}-{mo}-{g[0].zfill(2)}"
                elif len(g)>2 and g[0].isalpha():
                    mo = months_map.get(g[0].lower()[:3])
                    if mo: txn_date = f"{g[2]}-{mo}-{g[1].zfill(2)}"
                else:
                    yr = g[2] if len(g[2])==4 else "20"+g[2]
                    txn_date = f"{yr}-{g[1].zfill(2)}-{g[0].zfill(2)}"
                datetime.strptime(txn_date,"%Y-%m-%d"); break
            except (ValueError,IndexError):
                txn_date = default_date or date.today().isoformat()

    auto_cat = auto_categorise(merchant or text)
    category = auto_cat if auto_cat else default_category
    description = (f"UPI: {merchant}" if merchant else "UPI Transaction")[:200]
    return {"amount":amount,"category":category,"description":description,"date":txn_date}

def auto_categorise(text):
    text = text.lower()
    rules = {
        "Food":["zomato","swiggy","restaurant","food","cafe","pizza","burger","hotel",
                "dhaba","bakers","bakery","mcdonalds","kfc","subway","dominos","starbucks",
                "tea","coffee","biryani","mess","eatery","dine"],
        "Travel":["ola","uber","rapido","irctc","redbus","makemytrip","goibibo","petrol",
                  "fuel","cab","auto","railway","airport","flight","indigo","spicejet",
                  "yatra","bus","metro","fastag","toll"],
        "Shopping":["amazon","flipkart","myntra","ajio","nykaa","meesho","snapdeal","mall",
                    "store","mart","bazaar","retail","fashion","clothes","decathlon","ikea",
                    "zepto","blinkit","instamart","bigbasket","grofers","dmart","supermarket",
                    "grocery","reliance","tata cliq"],
        "Entertainment":["pvr","inox","netflix","spotify","hotstar","youtube","prime","zee5",
                         "sonyliv","game","bookmyshow","ticket","cinema","movie","concert","club"],
        "Health":["pharmacy","medical","apollo","cipla","netmeds","1mg","hospital","clinic",
                  "doctor","lab","diagnostic","chemist","medicine","health","gym","fitness"],
        "Education":["udemy","coursera","byju","unacademy","vedantu","school","college",
                     "university","tuition","books","stationery","library","exam","course","fees"],
    }
    for cat,kws in rules.items():
        if any(k in text for k in kws): return cat
    return None

init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
