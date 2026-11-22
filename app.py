
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import sqlite3
import os
import csv
import io

app = Flask(__name__)
app.secret_key = "student_performance_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "students.db")


# Database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create database table
def create_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            gender TEXT,
            age INTEGER,
            class_name TEXT,
            attendance REAL,
            study_hours REAL,
            assignment_score REAL,
            exam_score REAL
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Add student
@app.route("/add_student", methods=["POST"])
def add_student():

    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    gender = request.form.get("gender", "")
    class_name = request.form.get("class", "").strip()

    try:
        age = int(request.form.get("age", ""))
        attendance = float(request.form.get("attendance", ""))
        study_hours = float(request.form.get("study_hours", ""))
        assignment_score = float(request.form.get("assignment_score", ""))
        exam_score = float(request.form.get("exam_score", ""))

        if not student_id or not student_name or not class_name:
            raise ValueError("Please fill all required fields.")

        if age <= 0 or not 0 <= attendance <= 100:
            raise ValueError("Check age and attendance values.")

        if study_hours < 0:
            raise ValueError("Study hours cannot be negative.")

        if not 0 <= assignment_score <= 100:
            raise ValueError("Assignment score must be 0 to 100.")

        if not 0 <= exam_score <= 100:
            raise ValueError("Exam score must be 0 to 100.")

    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT id FROM students WHERE student_id = ?",
        (student_id,)
    ).fetchone()

    if existing:
        conn.close()
        flash("Student ID already exists!", "error")
        return redirect(url_for("home"))

    conn.execute("""
        INSERT INTO students (
            student_id, student_name, gender, age,
            class_name, attendance, study_hours,
            assignment_score, exam_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, student_name, gender, age,
        class_name, attendance, study_hours,
        assignment_score, exam_score
    ))

    conn.commit()
    conn.close()

    flash("Student added successfully!", "success")
    return redirect(url_for("dashboard"))


# Student performance prediction logic
def predict_performance(student):

    score = student["exam_score"]
    attendance = student["attendance"]
    study_hours = student["study_hours"]

    if score >= 75 and attendance >= 75:
        prediction = "High Performer"
        suggestion = "Excellent! Maintain your performance."

    elif score >= 40 and attendance >= 60:
        prediction = "Average Performer"
        suggestion = "Improve study hours and practice regularly."

    else:
        prediction = "Needs Improvement"
        suggestion = "Improve attendance and focus more on studies."

    return prediction, suggestion


# Dashboard
@app.route("/dashboard")
def dashboard():

    conn = get_db_connection()

    students = conn.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    total = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    avg_attendance = conn.execute(
        "SELECT AVG(attendance) FROM students"
    ).fetchone()[0] or 0

    avg_exam = conn.execute(
        "SELECT AVG(exam_score) FROM students"
    ).fetchone()[0] or 0

    avg_assignment = conn.execute(
        "SELECT AVG(assignment_score) FROM students"
    ).fetchone()[0] or 0

    passed = conn.execute(
        "SELECT COUNT(*) FROM students WHERE exam_score >= 40"
    ).fetchone()[0]

    failed = total - passed

    chart_names = [s["student_name"] for s in students]
    chart_scores = [s["exam_score"] for s in students]

    conn.close()

    pass_percentage = (passed / total * 100) if total else 0

    return render_template(
        "dashboard.html",
        students=students,
        total=total,
        attendance=round(avg_attendance, 2),
        marks=round(avg_exam, 2),
        assignment=round(avg_assignment, 2),
        passed=passed,
        failed=failed,
        pass_percentage=round(pass_percentage, 2),
        chart_names=chart_names,
        chart_scores=chart_scores
    )


# Search students
@app.route("/search")
def search():

    keyword = request.args.get("q", "").strip()

    conn = get_db_connection()

    students = conn.execute("""
        SELECT * FROM students
        WHERE student_id LIKE ?
        OR student_name LIKE ?
        OR class_name LIKE ?
        ORDER BY id DESC
    """, (
        "%" + keyword + "%",
        "%" + keyword + "%",
        "%" + keyword + "%"
    )).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        students=students,
        total=len(students),
        attendance=0,
        marks=0,
        assignment=0,
        passed=0,
        failed=0,
        pass_percentage=0,
        chart_names=[],
        chart_scores=[],
        search_mode=True,
        keyword=keyword
    )


# Edit student page
@app.route("/edit/<int:student_record_id>")
def edit_student(student_record_id):

    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_record_id,)
    ).fetchone()

    conn.close()

    if student is None:
        flash("Student not found!", "error")
        return redirect(url_for("dashboard"))

    return render_template("edit_student.html", student=student)


# Update student
@app.route("/update/<int:student_record_id>", methods=["POST"])
def update_student(student_record_id):

    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    gender = request.form.get("gender", "")
    class_name = request.form.get("class", "").strip()

    try:
        age = int(request.form.get("age", ""))
        attendance = float(request.form.get("attendance", ""))
        study_hours = float(request.form.get("study_hours", ""))
        assignment_score = float(request.form.get("assignment_score", ""))
        exam_score = float(request.form.get("exam_score", ""))

        if not student_id or not student_name or not class_name:
            raise ValueError("Please fill all required fields.")

        if age <= 0 or not 0 <= attendance <= 100:
            raise ValueError("Check age and attendance values.")

        if study_hours < 0:
            raise ValueError("Study hours cannot be negative.")

        if not 0 <= assignment_score <= 100:
            raise ValueError("Assignment score must be 0 to 100.")

        if not 0 <= exam_score <= 100:
            raise ValueError("Exam score must be 0 to 100.")

    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for(
            "edit_student",
            student_record_id=student_record_id
        ))

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT id FROM students WHERE student_id = ? AND id != ?",
        (student_id, student_record_id)
    ).fetchone()

    if existing:
        conn.close()
        flash("Student ID already exists!", "error")
        return redirect(url_for(
            "edit_student",
            student_record_id=student_record_id
        ))

    result = conn.execute("""
        UPDATE students SET
            student_id = ?,
            student_name = ?,
            gender = ?,
            age = ?,
            class_name = ?,
            attendance = ?,
            study_hours = ?,
            assignment_score = ?,
            exam_score = ?
        WHERE id = ?
    """, (
        student_id, student_name, gender, age,
        class_name, attendance, study_hours,
        assignment_score, exam_score,
        student_record_id
    ))

    if result.rowcount == 0:
        conn.close()
        flash("Student not found!", "error")
        return redirect(url_for("dashboard"))

    conn.commit()
    conn.close()

    flash("Student details updated successfully!", "success")

    return redirect(url_for("dashboard"))


# Individual student prediction
@app.route("/prediction/<int:student_record_id>")
def student_prediction(student_record_id):

    conn = get_db_connection()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_record_id,)
    ).fetchone()

    conn.close()

    if student is None:
        flash("Student not found!", "error")
        return redirect(url_for("dashboard"))

    prediction, suggestion = predict_performance(student)

    return render_template(
        "prediction.html",
        student=student,
        prediction=prediction,
        suggestion=suggestion
    )


# Export CSV
@app.route("/export_csv")
def export_csv():

    conn = get_db_connection()

    students = conn.execute("""
        SELECT student_id, student_name, gender, age,
        class_name, attendance, study_hours,
        assignment_score, exam_score
        FROM students
        ORDER BY id
    """).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Student ID", "Student Name", "Gender",
        "Age", "Class", "Attendance",
        "Study Hours", "Assignment Score", "Exam Score"
    ])

    for student in students:
        writer.writerow(list(student))

    response = make_response("\ufeff" + output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=student_performance_data.csv"
    )

    response.headers["Content-Type"] = "text/csv; charset=utf-8"

    return response


# Delete student
@app.route("/delete/<int:student_record_id>", methods=["POST"])
def delete_student(student_record_id):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_record_id,)
    )

    conn.commit()
    conn.close()

    flash("Student record deleted.", "success")

    return redirect(url_for("dashboard"))


# Start application
if __name__ == "__main__":
    create_table()
    app.run(debug=True)
