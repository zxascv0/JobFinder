from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "jobfinder_secret_key"

API_URL = "https://remotive.com/api/remote-jobs"


# ==========================
# Database connection
# ==========================
def get_db():
    conn = sqlite3.connect("jobs.db")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================
# Register
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users(username, email, password)
                VALUES (?, ?, ?)
            """, (username, email, hashed_password))

            conn.commit()
            flash("Account Created Successfully")

            return redirect("/login")

        except:
            flash("Username or Email Already Exists")

        finally:
            conn.close()

    return render_template("register.html")


# ==========================
# Login
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")

        flash("Invalid Email or Password")

    return render_template("login.html")


# ==========================
# Logout
# ==========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==========================
# Save Search History
# ==========================
def save_history(user_id, keyword):
    conn = get_db()

    conn.execute("""
        INSERT INTO search_history(user_id, keyword)
        VALUES (?, ?)
    """, (user_id, keyword))

    conn.commit()
    conn.close()


# ==========================
# Search Jobs
# ==========================
def search_jobs(keyword):
    jobs = []

    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()

        for job in data.get("jobs", []):
            if keyword.lower() in job.get("title", "").lower():

                jobs.append({
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location": job.get("candidate_required_location", "Remote"),
                    "type": job.get("job_type", "Unknown"),
                    "url": job.get("url")
                })

        return jobs[:30]

    except:
        return []


# ==========================
# Home
# ==========================
@app.route("/", methods=["GET", "POST"])
def home():
    jobs = []
    search = ""

    if request.method == "POST":
        search = request.form.get("job")

        if search:
            jobs = search_jobs(search)

            if "user_id" in session:
                save_history(session["user_id"], search)

    return render_template("index.html", jobs=jobs, search=search)


# ==========================
# History
# ==========================
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    history_data = conn.execute("""
        SELECT keyword, id
        FROM search_history
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("history.html", history=history_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)