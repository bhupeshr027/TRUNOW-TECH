import csv
import os
import sqlite3
from contextlib import closing
from datetime import date, datetime
from functools import wraps
from io import StringIO

from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "trunow.db")
UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
PROFILE_UPLOAD = os.path.join(UPLOAD_ROOT, "profiles")
ATTENDANCE_UPLOAD = os.path.join(UPLOAD_ROOT, "attendance")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


app = Flask(__name__)
app.config["SECRET_KEY"] = "trunow-secret-key-change-me"
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

EMPLOYEE_SEED_DATA = [
    {"employee_id": "EMP001", "full_name": "Selvam", "username": "selvam", "password": "Selvam@2026"},
    {"employee_id": "EMP002", "full_name": "Rajesh Sagar", "username": "rajesh.sagar", "password": "Rajesh@2026"},
    {"employee_id": "EMP003", "full_name": "Rajaram D", "username": "rajaram.d", "password": "Rajaram@2026"},
    {"employee_id": "EMP004", "full_name": "Vikraman", "username": "vikraman", "password": "Vikraman@2026"},
    {"employee_id": "EMP005", "full_name": "Bikesh Das", "username": "bikesh.das", "password": "Bikesh@2026"},
    {"employee_id": "EMP006", "full_name": "Kavindra Kumar", "username": "kavindra.kumar", "password": "Kavindra@2026"},
    {"employee_id": "EMP007", "full_name": "Balakrishnan E", "username": "balakrishnan.e", "password": "Bala@2026"},
    {"employee_id": "EMP008", "full_name": "Rajasekar K", "username": "rajasekar.k", "password": "Rajasekar@2026"},
    {"employee_id": "EMP009", "full_name": "Vetrivel S", "username": "vetrivel.s", "password": "Vetrivel@2026"},
    {"employee_id": "EMP010", "full_name": "Jagdish Yadav", "username": "jagdish.yadav", "password": "Jagdish@2026"},
    {"employee_id": "EMP011", "full_name": "Mani Vannan", "username": "mani.vannan", "password": "Mani@2026"},
    {"employee_id": "EMP012", "full_name": "Mohanraj", "username": "mohanraj", "password": "Mohanraj@2026"},
    {"employee_id": "EMP013", "full_name": "Dinabandhu Malik", "username": "dinabandhu.malik", "password": "Dinabandhu@2026"},
    {"employee_id": "EMP014", "full_name": "Asath M", "username": "asath.m", "password": "Asath@2026"},
    {"employee_id": "EMP015", "full_name": "Ayub Khan", "username": "ayub.khan", "password": "Ayub@2026"},
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_directories():
    os.makedirs(PROFILE_UPLOAD, exist_ok=True)
    os.makedirs(ATTENDANCE_UPLOAD, exist_ok=True)


def save_uploaded_file(file_storage, folder):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    final_name = f"{timestamp}_{filename}"
    file_storage.save(os.path.join(folder, final_name))
    return final_name


def log_activity(user_type, user_id, action):
    execute_db(
        "INSERT INTO activity_logs (user_type, user_id, action, created_at) VALUES (?, ?, ?, ?)",
        (user_type, user_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def init_db():
    ensure_directories()
    schema = """
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL,
        designation TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        profile_photo TEXT,
        status TEXT NOT NULL DEFAULT 'Active',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        clock_in_time TEXT,
        clock_out_time TEXT,
        latitude TEXT,
        longitude TEXT,
        location_text TEXT,
        photo TEXT,
        status TEXT NOT NULL DEFAULT 'Present',
        created_at TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        assigned_to INTEGER NOT NULL,
        priority TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        remarks TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (assigned_to) REFERENCES employees (id)
    );

    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL,
        supplier TEXT NOT NULL,
        purchase_date TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """
    with closing(sqlite3.connect(DATABASE)) as db:
        db.executescript(schema)
        db.commit()

    with closing(sqlite3.connect(DATABASE)) as db:
        db.row_factory = sqlite3.Row
        admin = db.execute("SELECT id FROM admins WHERE username = ?", ("admin",)).fetchone()
        if not admin:
            db.execute(
                "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                (
                    "admin",
                    generate_password_hash("admin123"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for index, employee in enumerate(EMPLOYEE_SEED_DATA, start=1):
            phone = f"900000{index:04d}"
            email = f"{employee['username']}@trunowindia.com"
            existing_employee = db.execute(
                "SELECT id FROM employees WHERE username = ?", (employee["username"],)
            ).fetchone()
            if existing_employee:
                db.execute(
                    """
                    UPDATE employees
                    SET employee_id = ?, full_name = ?, phone = ?, email = ?, department = ?, designation = ?, password_hash = ?, status = ?
                    WHERE username = ?
                    """,
                    (
                        employee["employee_id"],
                        employee["full_name"],
                        phone,
                        email,
                        "Operations",
                        "Employee",
                        generate_password_hash(employee["password"]),
                        "Active",
                        employee["username"],
                    ),
                )
            else:
                db.execute(
                    """
                    INSERT INTO employees
                    (employee_id, full_name, username, phone, email, department, designation, password_hash, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        employee["employee_id"],
                        employee["full_name"],
                        employee["username"],
                        phone,
                        email,
                        "Operations",
                        "Employee",
                        generate_password_hash(employee["password"]),
                        "Active",
                        created_at,
                    ),
                )

        stock_count = db.execute("SELECT COUNT(*) AS count FROM stock").fetchone()["count"]
        if stock_count == 0:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.executemany(
                """
                INSERT INTO stock
                (item_name, category, quantity, unit, supplier, purchase_date, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Cat6 Cable Box",
                        "Cabling",
                        24,
                        "Boxes",
                        "NetSource India",
                        "2026-04-10",
                        "Available",
                        created_at,
                        created_at,
                    ),
                    (
                        "Fiber Patch Panel",
                        "Fiber Optics",
                        5,
                        "Units",
                        "OptiLink Systems",
                        "2026-04-21",
                        "Low Stock",
                        created_at,
                        created_at,
                    ),
                ],
            )
        db.commit()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_type") != "admin":
            flash("Please login as admin to continue.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def employee_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_type") != "employee":
            flash("Please login as employee to continue.", "warning")
            return redirect(url_for("employee_login"))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    current_employee = None
    if session.get("user_type") == "employee" and session.get("user_id"):
        current_employee = query_db(
            "SELECT * FROM employees WHERE id = ?", (session["user_id"],), one=True
        )
    return {
        "current_year": 2026,
        "session_user_type": session.get("user_type"),
        "current_employee": current_employee,
    }


@app.route("/")
def index():
    employees_count = query_db("SELECT COUNT(*) AS count FROM employees", one=True)["count"]
    active_projects = query_db("SELECT COUNT(*) AS count FROM tasks WHERE status != 'Completed'", one=True)[
        "count"
    ]
    return render_template(
        "index.html",
        employees_count=employees_count,
        active_projects=active_projects,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("admin_login.html")

        admin = query_db("SELECT * FROM admins WHERE username = ?", (username,), one=True)
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["user_type"] = "admin"
            session["user_id"] = admin["id"]
            session["username"] = admin["username"]
            log_activity("admin", admin["id"], "Logged into admin portal")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


@app.route("/employee/login", methods=["GET", "POST"])
def employee_login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()
        if not identifier or not password:
            flash("Username or phone and password are required.", "danger")
            return render_template("employee_login.html")

        employee = query_db(
            "SELECT * FROM employees WHERE username = ? OR phone = ?",
            (identifier, identifier),
            one=True,
        )
        if employee and check_password_hash(employee["password_hash"], password):
            session.clear()
            session["user_type"] = "employee"
            session["user_id"] = employee["id"]
            session["username"] = employee["username"]
            log_activity("employee", employee["id"], "Logged into employee portal")
            return redirect(url_for("employee_dashboard"))

        flash("Invalid employee credentials.", "danger")
    return render_template("employee_login.html")


@app.route("/logout")
def logout():
    user_type = session.get("user_type")
    user_id = session.get("user_id")
    if user_type and user_id:
        log_activity(user_type, user_id, "Logged out")
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_employees = query_db("SELECT COUNT(*) AS count FROM employees", one=True)["count"]
    today = date.today().isoformat()
    present_today = query_db(
        "SELECT COUNT(DISTINCT employee_id) AS count FROM attendance WHERE date = ?",
        (today,),
        one=True,
    )["count"]
    pending_tasks = query_db(
        "SELECT COUNT(*) AS count FROM tasks WHERE status != 'Completed'", one=True
    )["count"]
    stock_items = query_db("SELECT COUNT(*) AS count FROM stock", one=True)["count"]
    recent_activity = query_db(
        """
        SELECT a.*, e.full_name
        FROM activity_logs a
        LEFT JOIN employees e ON a.user_type = 'employee' AND a.user_id = e.id
        ORDER BY a.created_at DESC
        LIMIT 8
        """
    )
    low_stock = query_db("SELECT * FROM stock WHERE quantity <= 5 ORDER BY quantity ASC LIMIT 5")
    return render_template(
        "admin/dashboard.html",
        total_employees=total_employees,
        present_today=present_today,
        pending_tasks=pending_tasks,
        stock_items=stock_items,
        recent_activity=recent_activity,
        low_stock=low_stock,
        today=today,
    )


@app.route("/admin/employees")
@admin_required
def admin_employees():
    search = request.args.get("search", "").strip()
    if search:
        employees = query_db(
            """
            SELECT * FROM employees
            WHERE full_name LIKE ? OR username LIKE ? OR department LIKE ? OR designation LIKE ?
            ORDER BY created_at DESC
            """,
            tuple([f"%{search}%"] * 4),
        )
    else:
        employees = query_db("SELECT * FROM employees ORDER BY created_at DESC")
    return render_template("admin/employees.html", employees=employees, search=search)


@app.route("/admin/employees/add", methods=["GET", "POST"])
@admin_required
def add_employee():
    if request.method == "POST":
        fields = {
            "employee_id": request.form.get("employee_id", "").strip(),
            "full_name": request.form.get("full_name", "").strip(),
            "username": request.form.get("username", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "department": request.form.get("department", "").strip(),
            "designation": request.form.get("designation", "").strip(),
            "password": request.form.get("password", "").strip(),
            "status": request.form.get("status", "Active").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all employee fields.", "danger")
            return render_template("admin/add_employee.html", employee=fields)

        photo_name = save_uploaded_file(request.files.get("profile_photo"), PROFILE_UPLOAD)
        try:
            execute_db(
                """
                INSERT INTO employees
                (employee_id, full_name, username, phone, email, department, designation, password_hash, profile_photo, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["employee_id"],
                    fields["full_name"],
                    fields["username"],
                    fields["phone"],
                    fields["email"],
                    fields["department"],
                    fields["designation"],
                    generate_password_hash(fields["password"]),
                    photo_name,
                    fields["status"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            log_activity("admin", session["user_id"], f"Added employee {fields['full_name']}")
            flash("Employee added successfully.", "success")
            return redirect(url_for("admin_employees"))
        except sqlite3.IntegrityError:
            flash("Employee ID, username, phone, or email already exists.", "danger")
    return render_template("admin/add_employee.html", employee=None)


@app.route("/admin/employees/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_employee(id):
    employee = query_db("SELECT * FROM employees WHERE id = ?", (id,), one=True)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for("admin_employees"))

    if request.method == "POST":
        fields = {
            "employee_id": request.form.get("employee_id", "").strip(),
            "full_name": request.form.get("full_name", "").strip(),
            "username": request.form.get("username", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "department": request.form.get("department", "").strip(),
            "designation": request.form.get("designation", "").strip(),
            "status": request.form.get("status", "Active").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all employee fields.", "danger")
            return render_template("admin/add_employee.html", employee=fields, edit_mode=True, employee_row=employee)

        photo_name = save_uploaded_file(request.files.get("profile_photo"), PROFILE_UPLOAD)
        password = request.form.get("password", "").strip()
        password_hash = employee["password_hash"] if not password else generate_password_hash(password)
        final_photo = photo_name or employee["profile_photo"]
        try:
            execute_db(
                """
                UPDATE employees
                SET employee_id = ?, full_name = ?, username = ?, phone = ?, email = ?, department = ?, designation = ?, password_hash = ?, profile_photo = ?, status = ?
                WHERE id = ?
                """,
                (
                    fields["employee_id"],
                    fields["full_name"],
                    fields["username"],
                    fields["phone"],
                    fields["email"],
                    fields["department"],
                    fields["designation"],
                    password_hash,
                    final_photo,
                    fields["status"],
                    id,
                ),
            )
            log_activity("admin", session["user_id"], f"Updated employee {fields['full_name']}")
            flash("Employee updated successfully.", "success")
            return redirect(url_for("admin_employees"))
        except sqlite3.IntegrityError:
            flash("Employee ID, username, phone, or email already exists.", "danger")

    return render_template("admin/add_employee.html", employee=employee, edit_mode=True, employee_row=employee)


@app.route("/admin/employees/delete/<int:id>", methods=["POST"])
@admin_required
def delete_employee(id):
    employee = query_db("SELECT * FROM employees WHERE id = ?", (id,), one=True)
    if employee:
        execute_db("DELETE FROM employees WHERE id = ?", (id,))
        log_activity("admin", session["user_id"], f"Deleted employee {employee['full_name']}")
        flash("Employee deleted.", "success")
    return redirect(url_for("admin_employees"))


@app.route("/admin/attendance")
@admin_required
def admin_attendance():
    selected_date = request.args.get("date", "").strip()
    selected_employee = request.args.get("employee", "").strip()
    selected_department = request.args.get("department", "").strip()

    query = """
    SELECT a.*, e.full_name, e.employee_id AS emp_code, e.department
    FROM attendance a
    JOIN employees e ON a.employee_id = e.id
    WHERE 1 = 1
    """
    params = []
    if selected_date:
        query += " AND a.date = ?"
        params.append(selected_date)
    if selected_employee:
        query += " AND e.id = ?"
        params.append(selected_employee)
    if selected_department:
        query += " AND e.department = ?"
        params.append(selected_department)
    query += " ORDER BY a.date DESC, a.created_at DESC"

    attendance_rows = query_db(query, tuple(params))
    employees = query_db("SELECT id, full_name FROM employees ORDER BY full_name")
    departments = query_db("SELECT DISTINCT department FROM employees ORDER BY department")

    if request.args.get("export") == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Employee", "Employee ID", "Department", "Date", "Clock In", "Clock Out", "Location", "Status"]
        )
        for row in attendance_rows:
            writer.writerow(
                [
                    row["full_name"],
                    row["emp_code"],
                    row["department"],
                    row["date"],
                    row["clock_in_time"],
                    row["clock_out_time"],
                    row["location_text"],
                    row["status"],
                ]
            )
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance_report.csv"},
        )

    return render_template(
        "admin/attendance.html",
        attendance_rows=attendance_rows,
        employees=employees,
        departments=departments,
        selected_date=selected_date,
        selected_employee=selected_employee,
        selected_department=selected_department,
    )


@app.route("/admin/tasks")
@admin_required
def admin_tasks():
    tasks = query_db(
        """
        SELECT t.*, e.full_name
        FROM tasks t
        JOIN employees e ON t.assigned_to = e.id
        ORDER BY t.due_date ASC, t.updated_at DESC
        """
    )
    return render_template("admin/tasks.html", tasks=tasks)


@app.route("/admin/tasks/add", methods=["GET", "POST"])
@admin_required
def add_task():
    employees = query_db("SELECT id, full_name, department FROM employees WHERE status = 'Active' ORDER BY full_name")
    if request.method == "POST":
        fields = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "assigned_to": request.form.get("assigned_to", "").strip(),
            "priority": request.form.get("priority", "").strip(),
            "due_date": request.form.get("due_date", "").strip(),
            "status": request.form.get("status", "Pending").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all task fields.", "danger")
            return render_template("admin/tasks.html", tasks=query_db(
                """
                SELECT t.*, e.full_name
                FROM tasks t JOIN employees e ON t.assigned_to = e.id
                ORDER BY t.due_date ASC, t.updated_at DESC
                """
            ), employees=employees, show_form=True, task_form=fields)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db(
            """
            INSERT INTO tasks (title, description, assigned_to, priority, due_date, status, remarks, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fields["title"],
                fields["description"],
                fields["assigned_to"],
                fields["priority"],
                fields["due_date"],
                fields["status"],
                "",
                now,
                now,
            ),
        )
        assignee = query_db("SELECT full_name FROM employees WHERE id = ?", (fields["assigned_to"],), one=True)
        log_activity("admin", session["user_id"], f"Assigned task '{fields['title']}' to {assignee['full_name']}")
        flash("Task created successfully.", "success")
        return redirect(url_for("admin_tasks"))
    return render_template("admin/tasks.html", tasks=query_db(
        """
        SELECT t.*, e.full_name
        FROM tasks t JOIN employees e ON t.assigned_to = e.id
        ORDER BY t.due_date ASC, t.updated_at DESC
        """
    ), employees=employees, show_form=True)


@app.route("/admin/tasks/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_task(id):
    task = query_db("SELECT * FROM tasks WHERE id = ?", (id,), one=True)
    employees = query_db("SELECT id, full_name, department FROM employees WHERE status = 'Active' ORDER BY full_name")
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for("admin_tasks"))
    if request.method == "POST":
        fields = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "assigned_to": request.form.get("assigned_to", "").strip(),
            "priority": request.form.get("priority", "").strip(),
            "due_date": request.form.get("due_date", "").strip(),
            "status": request.form.get("status", "Pending").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all task fields.", "danger")
            return render_template("admin/tasks.html", tasks=query_db(
                """
                SELECT t.*, e.full_name
                FROM tasks t JOIN employees e ON t.assigned_to = e.id
                ORDER BY t.due_date ASC, t.updated_at DESC
                """
            ), employees=employees, show_form=True, edit_mode=True, task_form=fields, task_row=task)
        execute_db(
            """
            UPDATE tasks
            SET title = ?, description = ?, assigned_to = ?, priority = ?, due_date = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                fields["title"],
                fields["description"],
                fields["assigned_to"],
                fields["priority"],
                fields["due_date"],
                fields["status"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                id,
            ),
        )
        log_activity("admin", session["user_id"], f"Updated task '{fields['title']}'")
        flash("Task updated successfully.", "success")
        return redirect(url_for("admin_tasks"))

    tasks = query_db(
        """
        SELECT t.*, e.full_name
        FROM tasks t JOIN employees e ON t.assigned_to = e.id
        ORDER BY t.due_date ASC, t.updated_at DESC
        """
    )
    return render_template("admin/tasks.html", tasks=tasks, employees=employees, show_form=True, edit_mode=True, task_form=task, task_row=task)


@app.route("/admin/tasks/delete/<int:id>", methods=["POST"])
@admin_required
def delete_task(id):
    task = query_db("SELECT * FROM tasks WHERE id = ?", (id,), one=True)
    if task:
        execute_db("DELETE FROM tasks WHERE id = ?", (id,))
        log_activity("admin", session["user_id"], f"Deleted task '{task['title']}'")
        flash("Task deleted.", "success")
    return redirect(url_for("admin_tasks"))


@app.route("/admin/stock")
@admin_required
def admin_stock():
    stock_items = query_db("SELECT * FROM stock ORDER BY updated_at DESC")
    return render_template("admin/stock.html", stock_items=stock_items)


@app.route("/admin/stock/add", methods=["GET", "POST"])
@admin_required
def add_stock():
    if request.method == "POST":
        fields = {
            "item_name": request.form.get("item_name", "").strip(),
            "category": request.form.get("category", "").strip(),
            "quantity": request.form.get("quantity", "").strip(),
            "unit": request.form.get("unit", "").strip(),
            "supplier": request.form.get("supplier", "").strip(),
            "purchase_date": request.form.get("purchase_date", "").strip(),
            "status": request.form.get("status", "").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all stock fields.", "danger")
            return render_template("admin/stock.html", stock_items=query_db("SELECT * FROM stock ORDER BY updated_at DESC"), show_form=True, stock_form=fields)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db(
            """
            INSERT INTO stock (item_name, category, quantity, unit, supplier, purchase_date, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fields["item_name"],
                fields["category"],
                int(fields["quantity"]),
                fields["unit"],
                fields["supplier"],
                fields["purchase_date"],
                fields["status"],
                now,
                now,
            ),
        )
        log_activity("admin", session["user_id"], f"Added stock item {fields['item_name']}")
        flash("Stock item added successfully.", "success")
        return redirect(url_for("admin_stock"))
    return render_template("admin/stock.html", stock_items=query_db("SELECT * FROM stock ORDER BY updated_at DESC"), show_form=True)


@app.route("/admin/stock/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_stock(id):
    stock_item = query_db("SELECT * FROM stock WHERE id = ?", (id,), one=True)
    if not stock_item:
        flash("Stock item not found.", "danger")
        return redirect(url_for("admin_stock"))

    if request.method == "POST":
        fields = {
            "item_name": request.form.get("item_name", "").strip(),
            "category": request.form.get("category", "").strip(),
            "quantity": request.form.get("quantity", "").strip(),
            "unit": request.form.get("unit", "").strip(),
            "supplier": request.form.get("supplier", "").strip(),
            "purchase_date": request.form.get("purchase_date", "").strip(),
            "status": request.form.get("status", "").strip(),
        }
        if not all(fields.values()):
            flash("Please complete all stock fields.", "danger")
            return render_template("admin/stock.html", stock_items=query_db("SELECT * FROM stock ORDER BY updated_at DESC"), show_form=True, edit_mode=True, stock_form=fields, stock_row=stock_item)
        execute_db(
            """
            UPDATE stock
            SET item_name = ?, category = ?, quantity = ?, unit = ?, supplier = ?, purchase_date = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                fields["item_name"],
                fields["category"],
                int(fields["quantity"]),
                fields["unit"],
                fields["supplier"],
                fields["purchase_date"],
                fields["status"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                id,
            ),
        )
        log_activity("admin", session["user_id"], f"Updated stock item {fields['item_name']}")
        flash("Stock item updated successfully.", "success")
        return redirect(url_for("admin_stock"))
    return render_template("admin/stock.html", stock_items=query_db("SELECT * FROM stock ORDER BY updated_at DESC"), show_form=True, edit_mode=True, stock_form=stock_item, stock_row=stock_item)


@app.route("/admin/stock/delete/<int:id>", methods=["POST"])
@admin_required
def delete_stock(id):
    stock_item = query_db("SELECT * FROM stock WHERE id = ?", (id,), one=True)
    if stock_item:
        execute_db("DELETE FROM stock WHERE id = ?", (id,))
        log_activity("admin", session["user_id"], f"Deleted stock item {stock_item['item_name']}")
        flash("Stock item deleted.", "success")
    return redirect(url_for("admin_stock"))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    attendance_summary = query_db(
        """
        SELECT e.full_name, COUNT(a.id) AS days_marked
        FROM employees e
        LEFT JOIN attendance a ON e.id = a.employee_id
        GROUP BY e.id
        ORDER BY days_marked DESC, e.full_name ASC
        """
    )
    task_summary = query_db(
        """
        SELECT status, COUNT(*) AS total
        FROM tasks
        GROUP BY status
        """
    )
    stock_summary = query_db(
        """
        SELECT category, SUM(quantity) AS total_quantity
        FROM stock
        GROUP BY category
        ORDER BY total_quantity DESC
        """
    )
    return render_template(
        "admin/reports.html",
        attendance_summary=attendance_summary,
        task_summary=task_summary,
        stock_summary=stock_summary,
    )


@app.route("/employee/dashboard")
@employee_required
def employee_dashboard():
    employee = query_db("SELECT * FROM employees WHERE id = ?", (session["user_id"],), one=True)
    today = date.today().isoformat()
    attendance_today = query_db(
        "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
        (session["user_id"], today),
        one=True,
    )
    tasks = query_db(
        "SELECT * FROM tasks WHERE assigned_to = ? ORDER BY due_date ASC, updated_at DESC",
        (session["user_id"],),
    )
    pending_attendance = not attendance_today or not attendance_today["clock_out_time"]
    alerts = []
    if pending_attendance:
        alerts.append("Attendance action pending for today.")
    for task in tasks:
        if task["status"] != "Completed" and task["due_date"] <= today:
            alerts.append(f"Task '{task['title']}' is due.")
    if tasks:
        alerts.append("Check newly assigned tasks and keep remarks updated.")
    return render_template(
        "employee/dashboard.html",
        employee=employee,
        attendance_today=attendance_today,
        tasks=tasks,
        alerts=alerts,
        today=today,
    )


@app.route("/employee/profile", methods=["GET", "POST"])
@employee_required
def employee_profile():
    employee = query_db("SELECT * FROM employees WHERE id = ?", (session["user_id"],), one=True)
    if request.method == "POST":
        photo_name = save_uploaded_file(request.files.get("profile_photo"), PROFILE_UPLOAD)
        if photo_name:
            execute_db("UPDATE employees SET profile_photo = ? WHERE id = ?", (photo_name, session["user_id"]))
            log_activity("employee", session["user_id"], "Updated profile photo")
            flash("Profile photo updated.", "success")
        else:
            flash("Please upload a valid image file.", "danger")
        return redirect(url_for("employee_profile"))
    return render_template("employee/profile.html", employee=employee)


@app.route("/employee/attendance", methods=["GET", "POST"])
@employee_required
def employee_attendance():
    employee = query_db("SELECT * FROM employees WHERE id = ?", (session["user_id"],), one=True)
    today = date.today().isoformat()
    attendance_today = query_db(
        "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
        (session["user_id"], today),
        one=True,
    )

    if request.method == "POST":
        action_type = request.form.get("action_type", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        location_text = request.form.get("location_text", "").strip()
        photo_name = save_uploaded_file(request.files.get("photo"), ATTENDANCE_UPLOAD)

        if not latitude or not longitude or not location_text:
            flash("Location details are required to mark attendance.", "danger")
            return redirect(url_for("employee_attendance"))

        now_time = datetime.now().strftime("%H:%M:%S")
        current_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if action_type == "clock_in":
            if attendance_today and attendance_today["clock_in_time"]:
                flash("You have already clocked in today.", "warning")
            else:
                execute_db(
                    """
                    INSERT INTO attendance
                    (employee_id, date, clock_in_time, latitude, longitude, location_text, photo, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["user_id"],
                        today,
                        now_time,
                        latitude,
                        longitude,
                        location_text,
                        photo_name,
                        "Present",
                        current_stamp,
                    ),
                )
                log_activity("employee", session["user_id"], "Marked clock-in attendance")
                flash("Clock-in captured successfully.", "success")
        elif action_type == "clock_out":
            if not attendance_today:
                flash("Please clock in before clocking out.", "danger")
            elif attendance_today["clock_out_time"]:
                flash("You have already clocked out today.", "warning")
            else:
                execute_db(
                    """
                    UPDATE attendance
                    SET clock_out_time = ?, latitude = ?, longitude = ?, location_text = ?, photo = COALESCE(?, photo)
                    WHERE id = ?
                    """,
                    (now_time, latitude, longitude, location_text, photo_name, attendance_today["id"]),
                )
                log_activity("employee", session["user_id"], "Marked clock-out attendance")
                flash("Clock-out captured successfully.", "success")
        else:
            flash("Invalid attendance action.", "danger")
        return redirect(url_for("employee_attendance"))

    attendance_history = query_db(
        "SELECT * FROM attendance WHERE employee_id = ? ORDER BY date DESC, created_at DESC",
        (session["user_id"],),
    )
    return render_template(
        "employee/attendance.html",
        employee=employee,
        attendance_today=attendance_today,
        attendance_history=attendance_history,
        today=today,
    )


@app.route("/employee/tasks")
@employee_required
def employee_tasks():
    tasks = query_db(
        "SELECT * FROM tasks WHERE assigned_to = ? ORDER BY due_date ASC, updated_at DESC",
        (session["user_id"],),
    )
    return render_template("employee/tasks.html", tasks=tasks, today=date.today().isoformat())


@app.route("/employee/tasks/update/<int:id>", methods=["POST"])
@employee_required
def update_employee_task(id):
    task = query_db(
        "SELECT * FROM tasks WHERE id = ? AND assigned_to = ?",
        (id, session["user_id"]),
        one=True,
    )
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for("employee_tasks"))

    status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()
    if status not in {"Pending", "In Progress", "Completed"}:
        flash("Invalid task status.", "danger")
        return redirect(url_for("employee_tasks"))

    execute_db(
        "UPDATE tasks SET status = ?, remarks = ?, updated_at = ? WHERE id = ?",
        (status, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id),
    )
    log_activity("employee", session["user_id"], f"Updated task '{task['title']}' to {status}")
    flash("Task updated successfully.", "success")
    return redirect(url_for("employee_tasks"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
