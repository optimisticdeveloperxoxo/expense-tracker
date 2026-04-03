# 💹 SpendSense — Personal Expense Tracker

A **full-stack personal expense tracker** built with Flask, SQLite, and a modern dark-themed UI.  
Developed as a PBL (Project-Based Learning) submission.

---

## 🚀 Features

| Feature | Details |
|---|---|
| **Dashboard** | Live stats, pie chart, category breakdown, recent transactions |
| **Add Expense** | Amount, category (7 options), date, description with validation |
| **Edit Expense** | Update any field in-place |
| **Delete Expense** | Confirm-before-delete safety prompt |
| **Monthly Budget** | Set a budget, see progress bar & overspend warning |
| **Category Filter** | Filter by month + category |
| **Charts** | Doughnut chart via Chart.js |
| **Responsive UI** | Works on mobile, tablet, and desktop |

---

## 🛠 Tech Stack

- **Backend**: Python 3.x + Flask
- **Database**: SQLite (via Python's built-in `sqlite3`)
- **Frontend**: HTML5 + CSS3 (custom, no Bootstrap needed) + Vanilla JS
- **Charts**: Chart.js v4
- **Fonts**: Syne + DM Sans (Google Fonts)

---

## 📁 Project Structure

```
project/
├── app.py               ← Flask application + routes
├── database.db          ← SQLite database (auto-created)
├── requirements.txt     ← Python dependencies
├── README.md
├── templates/
│   ├── base.html        ← Shared layout (nav, header)
│   ├── index.html       ← Dashboard page
│   ├── add.html         ← Add expense form
│   └── edit.html        ← Edit expense form
└── static/
    ├── style.css        ← All styles (dark theme)
    └── script.js        ← Mobile nav + animations
```

---

## ⚡ Quick Start

### 1. Install Python 3 (if not already installed)
```bash
python --version   # should be 3.8+
```

### 2. Install Flask
```bash
pip install flask
```

### 3. Run the App
```bash
cd project
python app.py
```

### 4. Open in Browser
```
http://127.0.0.1:5000
```

The database is created automatically on first run. No setup needed!

---

## 🔌 API Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Dashboard with filters |
| `/add` | GET / POST | Add expense form |
| `/edit/<id>` | GET / POST | Edit expense by ID |
| `/delete/<id>` | POST | Delete expense by ID |
| `/set_budget` | POST | Set monthly budget |
| `/api/chart_data` | GET | JSON data for Chart.js |

---

## 🎨 Design Highlights

- **Dark slate theme** with warm amber accents
- **Syne** display font for headings (bold, geometric)
- **DM Sans** for body text (clean, readable)
- Category-coded color system (🔴 Food, 🩵 Travel, 💛 Shopping, etc.)
- Animated stat cards and table row staggering
- Progress bar for budget tracking
- Modal for budget input

---

## 📊 Database Schema

```sql
CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    description TEXT,
    date        TEXT    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE budgets (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    month  TEXT    NOT NULL UNIQUE,
    amount REAL    NOT NULL
);
```

---

## 👨‍💻 Team / Credits

PBL Project — Computer Science / Information Technology  
Built with ❤️ using Flask + SQLite
