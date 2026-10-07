from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "iips-project-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "iips.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "jpg", "jpeg", "png", "mp4"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, description TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS resources(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT,
        filename TEXT NOT NULL, original_filename TEXT NOT NULL,
        file_type TEXT, uploaded_by INTEGER NOT NULL,
        category_id INTEGER, status TEXT NOT NULL DEFAULT 'pending',
        upload_date TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ratings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
        rating INTEGER NOT NULL, comment TEXT, created_at TEXT NOT NULL,
        UNIQUE(resource_id, student_id))""")

    for name in ["DBMS", "Python", "Java", "Web Development", "Artificial Intelligence", "Data Structures", "Computer Networks", "OOAD", "Compiler Design", "Other"]:
        cur.execute("INSERT OR IGNORE INTO categories(name, description) VALUES(?, ?)", (name, name + " learning resources"))

    users = [
        ("IIPS Student", "student@iips.com", "student123", "student"),
        ("IIPS Faculty", "faculty@iips.com", "faculty123", "faculty"),
        ("System Administrator", "admin@iips.com", "admin123", "admin")]
    for name, email, password, role in users:
        if not cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            cur.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                        (name, email, generate_password_hash(password), role, now()))
    con.commit()
    con.close()


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
def index():
    return redirect(url_for("resources"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if not name or not email or not password:
            flash("Please fill all fields.", "danger")
            return redirect(url_for("register"))
        if role not in ("student", "faculty"):
            role = "student"
        con = db()
        if con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            con.close()
            flash("Email is already registered.", "danger")
            return redirect(url_for("register"))
        con.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                    (name, email, generate_password_hash(password), role, now()))
        con.commit()
        con.close()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        con = db()
        user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        con.close()
        if user and check_password_hash(user["password"], password):
            session.update(user_id=user["id"], name=user["name"], email=user["email"], role=user["role"])
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("resources"))


@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    con = db()
    if session["role"] == "faculty":
        rows = con.execute("""SELECT r.*, c.name category_name FROM resources r
            LEFT JOIN categories c ON r.category_id=c.id
            WHERE r.uploaded_by=? ORDER BY r.upload_date DESC""", (session["user_id"],)).fetchall()
    else:
        rows = con.execute("""SELECT r.*, c.name category_name, u.name uploader FROM resources r
            LEFT JOIN categories c ON r.category_id=c.id LEFT JOIN users u ON r.uploaded_by=u.id
            WHERE r.status='approved' ORDER BY r.upload_date DESC LIMIT 10""").fetchall()
    con.close()
    return render_template("dashboard.html", resources=rows, role=session["role"])


@app.route("/resources")
def resources():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    con = db()
    query = """SELECT r.*, c.name category_name, u.name uploader FROM resources r
        LEFT JOIN categories c ON r.category_id=c.id LEFT JOIN users u ON r.uploaded_by=u.id
        WHERE r.status='approved'"""
    params = []
    if search:
        query += " AND (r.title LIKE ? OR r.description LIKE ? OR u.name LIKE ?)"
        value = f"%{search}%"
        params += [value, value, value]
    if category:
        query += " AND r.category_id=?"
        params.append(category)
    query += " ORDER BY r.upload_date DESC"
    rows = con.execute(query, params).fetchall()
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    con.close()
    return render_template("resources.html", resources=rows, categories=categories,
                           search=search, selected_category=category)


@app.route("/resource/<int:resource_id>")
def resource_detail(resource_id):
    con = db()
    resource = con.execute("""SELECT r.*, c.name category_name, u.name uploader FROM resources r
        LEFT JOIN categories c ON r.category_id=c.id LEFT JOIN users u ON r.uploaded_by=u.id
        WHERE r.id=?""", (resource_id,)).fetchone()
    if not resource:
        con.close()
        flash("Resource not found.", "danger")
        return redirect(url_for("resources"))
    ratings = con.execute("""SELECT rt.*, u.name student_name FROM ratings rt
        JOIN users u ON rt.student_id=u.id WHERE rt.resource_id=? ORDER BY rt.created_at DESC""", (resource_id,)).fetchall()
    average = con.execute("SELECT AVG(rating) value FROM ratings WHERE resource_id=?", (resource_id,)).fetchone()["value"]
    con.close()
    return render_template("resource_detail.html", resource=resource, ratings=ratings, average_rating=average)


@app.route("/upload", methods=["GET", "POST"])
@role_required("faculty", "admin")
def upload():
    con = db()
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id")
        file = request.files.get("file")
        if not title or not file or not file.filename:
            con.close()
            flash("Title and file are required.", "danger")
            return redirect(url_for("upload"))
        if not allowed(file.filename):
            con.close()
            flash("File type is not allowed.", "danger")
            return redirect(url_for("upload"))
        original = file.filename
        safe = secure_filename(original)
        base, ext = os.path.splitext(safe)
        filename = f"{base}_{int(datetime.now().timestamp())}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        status = "approved" if session["role"] == "admin" else "pending"
        con.execute("""INSERT INTO resources(title,description,filename,original_filename,file_type,
            uploaded_by,category_id,status,upload_date) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (title, description, filename, original, ext[1:].upper(), session["user_id"], category_id, status, now()))
        con.commit()
        con.close()
        flash("Resource uploaded successfully." + (" Waiting for admin approval." if status == "pending" else ""), "success")
        return redirect(url_for("dashboard"))
    con.close()
    return render_template("upload.html", categories=categories)


@app.route("/download/<int:resource_id>")
@login_required
def download(resource_id):
    con = db()
    resource = con.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
    con.close()
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for("resources"))
    if session["role"] == "student" and resource["status"] != "approved":
        flash("This resource is not approved yet.", "warning")
        return redirect(url_for("resource_detail", resource_id=resource_id))
    return send_from_directory(UPLOAD_FOLDER, resource["filename"], as_attachment=True,
                               download_name=resource["original_filename"])


@app.route("/resource/<int:resource_id>/rate", methods=["POST"])
@role_required("student")
def rate_resource(resource_id):
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()
    if rating not in (1, 2, 3, 4, 5):
        flash("Rating must be between 1 and 5.", "danger")
        return redirect(url_for("resource_detail", resource_id=resource_id))
    con = db()
    existing = con.execute("SELECT id FROM ratings WHERE resource_id=? AND student_id=?",
                           (resource_id, session["user_id"])).fetchone()
    if existing:
        con.execute("UPDATE ratings SET rating=?, comment=?, created_at=? WHERE id=?",
                     (rating, comment, now(), existing["id"]))
    else:
        con.execute("INSERT INTO ratings(resource_id,student_id,rating,comment,created_at) VALUES(?,?,?,?,?)",
                     (resource_id, session["user_id"], rating, comment, now()))
    con.commit()
    con.close()
    flash("Feedback saved successfully.", "success")
    return redirect(url_for("resource_detail", resource_id=resource_id))


@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    con = db()
    stats = {
        "users_count": con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
        "resources_count": con.execute("SELECT COUNT(*) n FROM resources").fetchone()["n"],
        "pending_count": con.execute("SELECT COUNT(*) n FROM resources WHERE status='pending'").fetchone()["n"],
        "approved_count": con.execute("SELECT COUNT(*) n FROM resources WHERE status='approved'").fetchone()["n"]}
    resources_list = con.execute("""SELECT r.*, c.name category_name, u.name uploader FROM resources r
        LEFT JOIN categories c ON r.category_id=c.id LEFT JOIN users u ON r.uploaded_by=u.id
        ORDER BY r.upload_date DESC""").fetchall()
    users = con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    categories = con.execute("SELECT * FROM categories ORDER BY name").fetchall()
    con.close()
    return render_template("admin.html", **stats, resources=resources_list, users=users, categories=categories)


@app.route("/admin/resource/<int:resource_id>/approve", methods=["POST"])
@role_required("admin")
def approve_resource(resource_id):
    con = db()
    con.execute("UPDATE resources SET status='approved' WHERE id=?", (resource_id,))
    con.commit(); con.close()
    flash("Resource approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/resource/<int:resource_id>/reject", methods=["POST"])
@role_required("admin")
def reject_resource(resource_id):
    con = db()
    con.execute("UPDATE resources SET status='rejected' WHERE id=?", (resource_id,))
    con.commit(); con.close()
    flash("Resource rejected.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/resource/<int:resource_id>/delete", methods=["POST"])
@role_required("admin")
def delete_resource(resource_id):
    con = db()
    resource = con.execute("SELECT filename FROM resources WHERE id=?", (resource_id,)).fetchone()
    if resource:
        path = os.path.join(UPLOAD_FOLDER, resource["filename"])
        if os.path.exists(path): os.remove(path)
        con.execute("DELETE FROM ratings WHERE resource_id=?", (resource_id,))
        con.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        con.commit(); flash("Resource deleted.", "success")
    con.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/category/add", methods=["POST"])
@role_required("admin")
def add_category():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin_dashboard"))
    con = db()
    try:
        con.execute("INSERT INTO categories(name,description) VALUES(?,?)", (name, description))
        con.commit(); flash("Category added.", "success")
    except sqlite3.IntegrityError:
        flash("Category already exists.", "warning")
    con.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("admin_dashboard"))
    con = db()
    for row in con.execute("SELECT filename FROM resources WHERE uploaded_by=?", (user_id,)).fetchall():
        path = os.path.join(UPLOAD_FOLDER, row["filename"])
        if os.path.exists(path): os.remove(path)
    con.execute("DELETE FROM ratings WHERE student_id=?", (user_id,))
    con.execute("DELETE FROM resources WHERE uploaded_by=?", (user_id,))
    con.execute("DELETE FROM users WHERE id=?", (user_id,))
    con.commit(); con.close()
    flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    con = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            con.execute("UPDATE users SET name=? WHERE id=?", (name, session["user_id"]))
            con.commit(); session["name"] = name
            flash("Profile updated.", "success")
        else:
            flash("Name cannot be empty.", "danger")
    user = con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    con.close()
    return render_template("profile.html", user=user)


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(error):
    flash("File is too large. Maximum size is 50 MB.", "danger")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    init_db()
    print("IIPS Digital Learning Resource Repository")
    print("Student: student@iips.com / student123")
    print("Faculty: faculty@iips.com / faculty123")
    print("Admin:   admin@iips.com / admin123")
    print("Open: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)

print()