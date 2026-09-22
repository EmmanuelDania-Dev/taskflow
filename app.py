from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

@app.route('/', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Inputs cannot be empty!!", "danger")
            return redirect(url_for("register"))

        connection = sqlite3.connect("tasks.db")
        value_exists = connection.execute("""
            SELECT EXISTS(
                SELECT 1
                FROM users
                WHERE email = ?
            )
        """, (email,)).fetchone()[0]

        if value_exists:
            flash("This email is already registered!!", "danger")
            return redirect(url_for("register"))
    
        hashed_password = generate_password_hash(password)

        cursor = connection.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, hashed_password))
        connection.commit()
        connection.close()

        user_id = cursor.lastrowid

        session["user_id"] = user_id

        return redirect(url_for("add_task"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Inputs cannot be empty!!", "warning")
            return redirect(url_for("login"))

        connection = sqlite3.connect("tasks.db")
        connection.row_factory = sqlite3.Row
        user = connection.execute("""
            SELECT * FROM users
            WHERE email = ?
            """, (email,)).fetchone()

        if user is None:
            flash("Wrong email or password", "danger")
            return redirect(url_for("login"))

        password_checked = check_password_hash(
            user["password_hash"],
            password
        )
        if not password_checked:
            flash("Wrong email or password", "danger")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]

        flash("Login Successfull!", "success")
        return redirect(url_for("add_task"))
    
    return render_template("login.html")

@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = sqlite3.connect("tasks.db")
    connection.row_factory = sqlite3.Row

    user = connection.execute(
        "SELECT username FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    if not user:
        session.clear()
        flash("User account not found. Please log in again.", "warning")
        return redirect(url_for("login"))

    username = user["username"]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not description:
            flash("Title or Description cannot be empty", "warning")
            return redirect(url_for("add_task"))

        connection = sqlite3.connect("tasks.db")

        connection.execute("""
            INSERT INTO tasks (title, description, user_id)
            VALUES (?, ?, ?)
        """, (title, description, user_id))

        connection.commit()
        connection.close()

        return redirect(url_for("display"))

    return render_template("index.html", username=username)

@app.route("/display")
def display():
    if "user_id" not in session:
        flash("You are not logged in!!", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    
    connection = sqlite3.connect("tasks.db")
    connection.row_factory = sqlite3.Row

    tasks = connection.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)).fetchall()

    stats = connection.execute("""
        SELECT 
            COUNT (*) AS total_tasks,
            SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) AS ongoing_tasks,
            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed_tasks
        FROM tasks WHERE user_id = ?
    """, (user_id,)).fetchone()

    connection.close()

    return render_template("display.html", tasks=tasks, stats=stats)

@app.route("/completed/<int:id>", methods=["POST"])
def completed(id):
    if "user_id" not in session:
        flash("Cannot mark task", "warning")
        return redirect(url_for("display"))
    user_id = session["user_id"]

    connection = sqlite3.connect("tasks.db")

    connection.execute("""
        UPDATE tasks
        SET COMPLETED = 1
        WHERE id = ?
        AND user_id = ?
    """, (id, user_id))

    connection.commit()
    connection.close()

    return redirect(url_for("display"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        flash("You can only edit your own tasks", "warning")
        return redirect(url_for("display"))
    user_id = session["user_id"]

    connection = sqlite3.connect("tasks.db")
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not description:
            flash("Title or Description cannot be empty", "warning")
            return redirect(url_for("add_task"))
        

        connection.execute("""
            UPDATE tasks
            SET title = ?, description = ?
            WHERE id = ?
            AND user_id = ?
        """, (title, description, id, user_id))
        connection.commit()
        connection.close()
        return redirect(url_for('display'))

    task = connection.execute("""
        SELECT * FROM tasks
        WHERE id = ?
        AND user_id = ?
        """, (id, user_id)).fetchone()
    if task is None:
        flash("Task not found!!", "warning")
        return redirect(url_for("display"))
    return render_template("edit.html", task=task)

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user_id" not in session:
        flash("Cannot delete task!", "warning")
        return redirect(url_for("display"))
    user_id = session["user_id"]

    connection = sqlite3.connect("tasks.db")

    connection.execute("""
        DELETE FROM tasks
        WHERE id = ?
        AND user_id = ?
        """, (id, user_id))
    connection.commit()
    connection.close()

    return redirect(url_for("display"))

@app.route('/delete_account', methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("login"))
    user_id = session["user_id"]

    connection = sqlite3.connect("tasks.db")

    connection.execute("""
        DELETE FROM tasks
        WHERE user_id = ?
    """, (user_id,))

    connection.execute("""
        DELETE from users
        WHERE id = ?
    """, (user_id,))

    connection.commit()
    connection.close()

    session.clear()

    flash("Your account has been deleted successfully", "success")
    return redirect(url_for("register"))

@app.route('/logout')
def logout():
    session.pop("user_id", None)
    flash("You have been logged out successfully!!", "success")

    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)