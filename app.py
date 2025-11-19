from flask import (
    Flask, render_template, request, send_file, send_from_directory,
    url_for, jsonify, redirect
)
import os
import csv
import base64
import datetime
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------------------------------
# BASE DIRECTORIES
# ---------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUBMISSIONS_DIR = os.path.join(BASE_DIR, "submissions")
DIAGRAM_FOLDER = os.path.join(BASE_DIR, "diagrams")
OVERLAY_FOLDER = os.path.join(BASE_DIR, "diagram_overlays")
QUESTIONS_DIR = os.path.join(BASE_DIR, "questions")
EXAMS_DIR = os.path.join(BASE_DIR, "exams")
ATTEMPTS_DIR = os.path.join(BASE_DIR, "attempts")
DRAWINGS_DIR = os.path.join(BASE_DIR, "drawings")

# Ensure folders exist
for d in [
    SUBMISSIONS_DIR, DIAGRAM_FOLDER, OVERLAY_FOLDER, QUESTIONS_DIR,
    EXAMS_DIR, ATTEMPTS_DIR, DRAWINGS_DIR
]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------
# 1. MAIN PAGE (Phase 1)
# ---------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_name = request.form.get("student_name", "Unknown")
        answer_text = request.form.get("answer_text", "")
        drawing_data = request.form.get("drawing_data", "")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{student_name}_{timestamp}".replace(" ", "_")

        # Save CSV
        with open(os.path.join(SUBMISSIONS_DIR, "answers.csv"), "a",
                  newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, student_name, answer_text])

        # Save drawing
        if drawing_data.startswith("data:image/png;base64,"):
            img_bytes = base64.b64decode(drawing_data.split(",")[1])
            with open(os.path.join(SUBMISSIONS_DIR, f"{filename_base}.png"), "wb") as img_file:
                img_file.write(img_bytes)

        return "Submission received!"

    return render_template("index.html")

# ---------------------------------------
# 2. LIST SUBMISSIONS
# ---------------------------------------
@app.route("/submissions")
def list_submissions():
    files = os.listdir(SUBMISSIONS_DIR)
    return render_template("submissions.html", files=files)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(os.path.join(SUBMISSIONS_DIR, filename), as_attachment=True)

# ---------------------------------------
# 3. DIAGRAM SERVE
# ---------------------------------------
@app.route("/get_diagram/<filename>")
def get_diagram(filename):
    return send_from_directory(DIAGRAM_FOLDER, filename)

@app.route("/get_overlay/<filename>")
def get_overlay(filename):
    return send_from_directory(OVERLAY_FOLDER, filename)

# ---------------------------------------
# 4. DIAGRAM DRAW PAGE
# ---------------------------------------
@app.route("/diagram/<diagram_name>")
def diagram(diagram_name):
    return render_template("diagram.html", diagram_name=diagram_name)

@app.route("/save_diagram", methods=["POST"])
def save_diagram():
    data = request.json
    image_data = data.get("imageData")
    diagram_name = secure_filename(data.get("sourceDiagram", "unknown"))

    if not image_data:
        return jsonify({"status": "error", "message": "No image data"}), 400

    img_base64 = image_data.split(",")[1]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"overlay_{diagram_name}_{timestamp}.png"
    filepath = os.path.join(OVERLAY_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(img_base64))

    return jsonify({"status": "success", "file": filename})

# ---------------------------------------
# 5. FIXED QUESTION (Phase 2/3)
# ---------------------------------------
@app.route("/question/<qid>")
def fixed_question(qid):
    questions = {
        "light_q5": {
            "diagram": "light_question.png",
            "text": """
                <p>(a) A ray of light is incident normally on a semicircular block.</p>
                <p>(i) Calculate the critical angle.</p>
                <p>(ii) Draw and describe the ray path.</p>
            """,
            "parts": ["(i) Critical angle", "(ii) Path explanation"]
        }
    }
    q = questions.get(qid)
    if not q:
        return "Question not found", 404

    return render_template(
        "question_template.html",
        diagram_filename=q["diagram"],
        question_text=q["text"],
        question_id=qid,
        parts=q["parts"]
    )

@app.route("/submit_fixed_question", methods=["POST"])
def submit_fixed_question():
    data = request.json or {}
    timestamp = data.get("timestamp", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    student = data.get("student", "Unknown").replace(" ", "_")
    qid = data.get("question", "unknown")
    diagram = data.get("diagram", "")
    answer = data.get("answer", "")

    fname = f"{student}_{timestamp}_{qid}.txt"
    with open(os.path.join(SUBMISSIONS_DIR, fname), "w", encoding="utf-8") as f:
        f.write(f"Student: {student}\nQuestion: {qid}\nDiagram: {diagram}\n\nAnswer:\n{answer}")

    return jsonify({"status": "Saved", "file": fname})

# ---------------------------------------
# 6. TEACHER UPLOAD SINGLE QUESTION (Phase 3)
# ---------------------------------------
@app.route("/upload_question")
def upload_question():
    return render_template("upload_question.html")

@app.route("/teacher/upload_question", methods=["POST"])
def teacher_upload_question():
    qid = request.form.get("question_id")
    if not qid:
        return "Missing question ID", 400

    q_folder = os.path.join(QUESTIONS_DIR, qid)
    os.makedirs(q_folder, exist_ok=True)

    question_image = request.files.get("question_image")
    diagram_image = request.files.get("diagram_image")

    question_image.save(os.path.join(q_folder, "question.png"))
    diagram_image.save(os.path.join(q_folder, "diagram.png"))

    meta = {
        "question_id": qid,
        "question_image": "question.png",
        "diagram_image": "diagram.png"
    }
    with open(os.path.join(q_folder, "meta.json"), "w") as f:
        json.dump(meta, f)

    link = url_for("exam_page", qid=qid, _external=True)
    return f"Uploaded! Student page: <a href='{link}'>{link}</a>"

# ---------------------------------------
# 7. STUDENT PAGE FOR SINGLE QUESTION
# ---------------------------------------
@app.route("/exam/<qid>")
def exam_page(qid):
    q_folder = os.path.join(QUESTIONS_DIR, qid)
    meta_path = os.path.join(q_folder, "meta.json")

    if not os.path.exists(meta_path):
        return "Question not found", 404

    with open(meta_path) as f:
        meta = json.load(f)

    return render_template(
        "exam_template.html",
        qid=qid,
        question_image=meta["question_image"],
        diagram_image=meta["diagram_image"]
    )

@app.route("/question_file/<qid>/<filename>")
def question_file(qid, filename):
    folder = os.path.join(QUESTIONS_DIR, qid)
    return send_from_directory(folder, filename)

# ---------------------------------------
# 8. SAVE STUDENT ANSWER FOR SINGLE QUESTION
# ---------------------------------------
@app.route("/save_exam_answer", methods=["POST"])
def save_exam_answer():
    data = request.json or {}
    qid = data.get("qid")
    student = data.get("studentName", "Unknown").replace(" ", "_")
    answer_text = data.get("answerText", "")
    overlay = data.get("overlayImage")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{qid}_{student}_{timestamp}"

    with open(os.path.join(SUBMISSIONS_DIR, f"{base}.txt"), "w") as f:
        f.write(answer_text)

    if overlay and overlay.startswith("data:image"):
        bytes_data = base64.b64decode(overlay.split(",")[1])
        with open(os.path.join(SUBMISSIONS_DIR, f"{base}.png"), "wb") as f:
            f.write(bytes_data)

    return jsonify({"status": "success"})

# ---------------------------------------
# 9. TEACHER: CREATE EXAM (Phase 4)
# ---------------------------------------
@app.route("/teacher/create_exam")
def teacher_create_exam():
    return render_template("create_exam.html")

@app.route("/teacher/save_exam", methods=["POST"])
def teacher_save_exam():
    data = request.json
    exam_id = data["exam_id"]
    exam_title = data["exam_title"]
    questions = data["questions"]

    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    os.makedirs(exam_folder, exist_ok=True)

    # Save meta.json
    meta = {
        "exam_id": exam_id,
        "title": exam_title,
        "num_questions": len(questions)
    }
    with open(os.path.join(exam_folder, "meta.json"), "w") as f:
        json.dump(meta, f, indent=4)

    # Save questions.json
    with open(os.path.join(exam_folder, "questions.json"), "w") as f:
        json.dump(questions, f, indent=4)

    preview_link = f"/exam/start/{exam_id}"
    return {"status": "success", "preview_url": preview_link}

# ---------------------------------------
# 10. START EXAM — LOAD meta.json + questions.json
# ---------------------------------------
@app.route("/exam/start/<exam_id>")
def start_exam(exam_id):
    exam_path = os.path.join(EXAMS_DIR, exam_id)

    meta_path = os.path.join(exam_path, "meta.json")
    qlist_path = os.path.join(exam_path, "questions.json")

    if not os.path.exists(meta_path) or not os.path.exists(qlist_path):
        return "Exam files missing (meta.json or questions.json)", 500

    with open(meta_path) as f:
        meta = json.load(f)

    with open(qlist_path) as f:
        questions = json.load(f)

    return render_template(
        "student_exam.html",
        exam_id=exam_id,
        exam_title=meta.get("title"),
        questions=questions
    )

# ---------------------------------------
# 11. SERVE EXAM FILES
# ---------------------------------------
@app.route("/exam_file/<exam_id>/<filename>")
def exam_file(exam_id, filename):
    folder = os.path.join(EXAMS_DIR, exam_id)
    return send_from_directory(folder, filename)

# ---------------------------------------
# 12. AUTOSAVE (Multi-question exam)
# ---------------------------------------
@app.route("/exam/autosave", methods=["POST"])
def exam_autosave():
    data = request.get_json()
    exam_id = data.get("exam_id")
    qindex = int(data.get("qindex"))
    student = data.get("studentName", "").replace(" ", "_")
    answer = data.get("answerText", "")
    overlay = data.get("overlayImage")

    exam_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    os.makedirs(exam_folder, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    overlay_filename = ""
    if overlay and overlay.startswith("data:image"):
        b64 = overlay.split(",")[1]
        overlay_filename = f"{exam_id}_{student}_{qindex}_{timestamp}.png"
        with open(os.path.join(DRAWINGS_DIR, overlay_filename), "wb") as f:
            f.write(base64.b64decode(b64))

    attempt_file = os.path.join(exam_folder, f"{student}.json")

    if os.path.exists(attempt_file):
        with open(attempt_file) as f:
            attempt = json.load(f)
    else:
        attempt = {"exam_id": exam_id, "student": student, "answers": {}}

    attempt["answers"][str(qindex)] = {
        "answerText": answer,
        "overlay_file": overlay_filename,
        "saved_at": timestamp
    }

    with open(attempt_file, "w") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status": "success"})

# ---------------------------------------
# 13. FINAL SUBMIT
# ---------------------------------------
@app.route("/exam/submit", methods=["POST"])
def exam_submit():
    data = request.get_json()
    exam_id = data.get("exam_id")
    student = data.get("studentName", "").replace(" ", "_")

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")
    if not os.path.exists(attempt_file):
        return jsonify({"status": "error", "message": "Attempt not found"}), 404

    with open(attempt_file) as f:
        attempt = json.load(f)

    attempt["submitted"] = True
    attempt["submitted_at"] = datetime.datetime.now().isoformat()

    with open(attempt_file, "w") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status": "success"})

# ---------------------------------------
# TEACHER MARKING DASHBOARD (Phase 4)
# ---------------------------------------
@app.route("/teacher/attempts/<exam_id>")
def teacher_attempts(exam_id):
    """
    List all student attempts for an exam.
    """
    exam_attempts_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    attempts = []
    if os.path.exists(exam_attempts_folder):
        for fname in os.listdir(exam_attempts_folder):
            if fname.lower().endswith(".json"):
                attempts.append(fname.replace(".json",""))
    return render_template("teacher_marking_list.html", exam_id=exam_id, attempts=attempts)


@app.route("/teacher/mark/<exam_id>/<student>", methods=["GET"])
def teacher_mark_attempt(exam_id, student):
    """
    Marking page for one student's attempt.
    Loads attempt JSON and displays each question with overlay image (if any).
    """
    student_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")
    if not os.path.exists(student_file):
        return f"Attempt not found for {student}", 404

    with open(student_file, "r", encoding="utf-8") as f:
        attempt = json.load(f)

    # Load exam question list for model answers / question metadata
    exam_meta = {}
    exam_questions = []
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    meta_path = os.path.join(exam_folder, "meta.json")
    qlist_path = os.path.join(exam_folder, "questions.json")
    if os.path.exists(meta_path):
        with open(meta_path) as mf:
            exam_meta = json.load(mf)
    if os.path.exists(qlist_path):
        with open(qlist_path) as qf:
            exam_questions = json.load(qf)

    # For convenience, build a list of question entries (qindex -> data)
    return render_template(
        "teacher_mark_attempt.html",
        exam_id=exam_id,
        student=student,
        attempt=attempt,
        questions=exam_questions,
        exam_meta=exam_meta
    )


@app.route("/teacher/save_marks/<exam_id>/<student>", methods=["POST"])
def teacher_save_marks(exam_id, student):
    """
    Saves marks/comments provided by teacher into the student's attempt JSON.
    Expects JSON: { marks: { "1": {score: X, comment: "..."}, "2": {...}}, overall_comment: "...", released: true/false }
    """
    payload = request.get_json() or {}
    exam_attempts_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    os.makedirs(exam_attempts_folder, exist_ok=True)
    student_file = os.path.join(exam_attempts_folder, f"{student}.json")
    if not os.path.exists(student_file):
        return jsonify({"status":"error","message":"Attempt not found"}), 404

    with open(student_file, "r", encoding="utf-8") as f:
        attempt = json.load(f)

    # attach grading info
    attempt['grading'] = {
        "marks": payload.get("marks", {}),
        "overall_comment": payload.get("overall_comment",""),
        "released": payload.get("released", False),
        "graded_at": datetime.datetime.now().isoformat(),
        "graded_by": payload.get("graded_by", "Teacher")
    }

    with open(student_file, "w", encoding="utf-8") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status":"success"})


# ---------------------------------------
# RUN
# ---------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
