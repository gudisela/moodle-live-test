# app.py (fixed full version)
from flask import (
    Flask, render_template, request, send_file, send_from_directory,
    url_for, jsonify
)
import os
import csv
import base64
import datetime
import json
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# -----------------------------
# BASE DIRECTORIES
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUBMISSIONS_DIR = os.path.join(BASE_DIR, "submissions")
DIAGRAM_FOLDER = os.path.join(BASE_DIR, "diagrams")
OVERLAY_FOLDER = os.path.join(BASE_DIR, "diagram_overlays")
QUESTIONS_DIR = os.path.join(BASE_DIR, "questions")
EXAMS_DIR = os.path.join(BASE_DIR, "exams")
ATTEMPTS_DIR = os.path.join(BASE_DIR, "attempts")
DRAWINGS_DIR = os.path.join(BASE_DIR, "drawings")


# create folders if not exist
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)
os.makedirs(DIAGRAM_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)
os.makedirs(EXAMS_DIR, exist_ok=True)
os.makedirs(ATTEMPTS_DIR, exist_ok=True)
os.makedirs(DRAWINGS_DIR, exist_ok=True)

# -----------------------------
# 1. Main text + drawing submission (Phase 1)
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_name = request.form.get("student_name", "Unknown")
        answer_text = request.form.get("answer_text", "")
        drawing_data = request.form.get("drawing_data", "")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{student_name}_{timestamp}".replace(" ", "_")

        # Save text (CSV)
        with open(os.path.join(SUBMISSIONS_DIR, "answers.csv"), "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, student_name, answer_text])

        # Save drawing
        if drawing_data and drawing_data.startswith("data:image/png;base64,"):
            img_bytes = base64.b64decode(drawing_data.split(",")[1])
            with open(os.path.join(SUBMISSIONS_DIR, f"{filename_base}.png"), "wb") as img_file:
                img_file.write(img_bytes)

        return "Submission received!"

    return render_template("index.html")

# -----------------------------
# 2. List submissions
# -----------------------------
@app.route("/submissions")
def list_submissions():
    files = os.listdir(SUBMISSIONS_DIR)
    return render_template("submissions.html", files=files)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(os.path.join(SUBMISSIONS_DIR, filename), as_attachment=True)

# -----------------------------
# 3. Serve background diagram (Phase 2)
# -----------------------------
@app.route("/get_diagram/<filename>")
def get_diagram(filename):
    return send_from_directory(DIAGRAM_FOLDER, filename)

# -----------------------------
# 4. Serve saved overlay drawing
# -----------------------------
@app.route("/get_overlay/<filename>")
def get_overlay(filename):
    return send_from_directory(OVERLAY_FOLDER, filename)

# -----------------------------
# 5. Diagram drawing page (Overlay tool)
# -----------------------------
@app.route("/diagram/<diagram_name>")
def diagram(diagram_name):
    """
    Example URL:
      /diagram/physics_light_q4.png
    Renders template 'diagram.html' (canvas overlay), using server route /get_diagram/<filename>
    """
    return render_template("diagram.html", diagram_name=diagram_name)

# -----------------------------
# 6. Save overlay drawing (Phase 2)
# -----------------------------
@app.route("/save_diagram", methods=["POST"])
def save_diagram():
    data = request.json
    image_data = data.get("imageData")
    diagram_name = data.get("sourceDiagram", "unknown")

    if not image_data:
        return jsonify({"status": "error", "message": "No image data received"}), 400

    img_base64 = image_data.split(",")[1]

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(diagram_name)
    filename = f"overlay_{safe_name}_{timestamp}.png"
    filepath = os.path.join(OVERLAY_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(img_base64))

    return jsonify({"status": "success", "file": filename})

# -----------------------------
# 7. Fixed question template (Phase 2/3)
# -----------------------------
@app.route("/question/<qid>")
def fixed_question(qid):
    # demo hard-coded questions map (you can replace with JSON files)
    questions = {
       "light_q5": {
            "diagram": "light_question.png",
            "text": """
                  <p>(a) A ray of light is incident normally on the curved surface of a semicircular block.</p>
                  <p>(i) Calculate the critical angle.</p>
                  <p>(ii) Draw and describe the path of the ray.</p>
            """,
            "parts": ["(i) Critical angle", "(ii) Ray path explanation"]
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
    student_raw = data.get("student", "Unknown")
    student = student_raw.replace(" ", "_")
    qid = data.get("question", "unknown")
    diagram = data.get("diagram", "")

    # save answer text
    fname = f"{student}_{timestamp}_{qid}.txt"
    with open(os.path.join(SUBMISSIONS_DIR, fname), "w", encoding="utf-8") as f:
        f.write("Student: " + student_raw + "\n")
        f.write("Question: " + qid + "\n")
        f.write("Diagram: " + diagram + "\n\n")
        f.write("Answer:\n" + data.get("answer", ""))

    return jsonify({"status": "Saved", "file": fname})

# -----------------------------
# 8. Teacher upload page (Phase 3)
# -----------------------------
@app.route("/upload_question")
def upload_question():
    return render_template("upload_question.html")

# Helper: ensure QUESTIONS_DIR exists (already created at top)
# QUESTIONS_DIR = os.path.join(BASE_DIR, "questions")  # created earlier as QUESTIONS_DIR

@app.route("/teacher/upload_question", methods=["POST"])
def teacher_upload_question():
    qid = request.form.get("question_id")
    question_image = request.files.get("question_image")
    diagram_image = request.files.get("diagram_image")

    if not qid:
        return "Missing question ID", 400

    # Folder for this question
    q_folder = os.path.join(QUESTIONS_DIR, qid)
    os.makedirs(q_folder, exist_ok=True)

    # Save question text image
    q_img_path = os.path.join(q_folder, "question.png")
    question_image.save(q_img_path)

    # Save diagram image
    d_img_path = os.path.join(q_folder, "diagram.png")
    diagram_image.save(d_img_path)

    # Save meta file
    meta = {
        "question_id": qid,
        "question_image": "question.png",
        "diagram_image": "diagram.png"
    }
    with open(os.path.join(q_folder, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)

    # Return a link to the generated student page
    student_url = url_for('exam_page', qid=qid, _external=True)
    return f"Question {qid} uploaded successfully!<br>Student page: <a href='{student_url}' target='_blank'>{student_url}</a>"

# -----------------------------
# 9. Student exam page (Phase 3)
# -----------------------------
@app.route("/exam/<qid>")
def exam_page(qid):
    q_folder = os.path.join(QUESTIONS_DIR, qid)
    meta_path = os.path.join(q_folder, "meta.json")

    if not os.path.exists(meta_path):
        return "Question not found", 404

    with open(meta_path, "r", encoding="utf-8") as f:
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

@app.route("/save_exam_answer", methods=["POST"])
def save_exam_answer():
    data = request.json or {}

    qid = data.get("qid", "unknown")
    student_name = data.get("studentName", "Unknown").replace(" ", "_")
    answer_text = data.get("answerText", "")
    overlay_base64 = data.get("overlayImage", "")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_base = f"{qid}_{student_name}_{timestamp}".replace(" ", "_")

    # Save answer text
    with open(os.path.join(SUBMISSIONS_DIR, f"{save_base}.txt"), "w", encoding="utf-8") as f:
        f.write("Question: " + qid + "\n")
        f.write("Student: " + student_name + "\n\n")
        f.write("Answer:\n" + answer_text)

    # Save drawing overlay
    if overlay_base64 and overlay_base64.startswith("data:image"):
        overlay_bytes = base64.b64decode(overlay_base64.split(",")[1])
        with open(os.path.join(SUBMISSIONS_DIR, f"{save_base}.png"), "wb") as f:
            f.write(overlay_bytes)

    return jsonify({"status": "success", "file": f"{save_base}.txt"})
# -----------------------------
# 10. Teacher creare exam form(Phase 4)
# -----------------------------

# --- Teacher: create exam form ---
@app.route("/teacher/create_exam")
def teacher_create_exam():
    # render a page with a basic form to enter exam meta and upload multiple questions
    return render_template("create_exam.html")

# --- Teacher: save exam (multipart/form-data) ---
@app.route("/teacher/save_exam", methods=["POST"])
def teacher_save_exam():
    """
    Expects form data:
      exam_id (optional) -> generated if empty
      title
      created_by
      For each question i:
        qid_i, marks_i, instruction_i, model_i, question_file_i, diagram_file_i (optional)
    We'll accept up to N questions from the form (front-end will send).
    """
    
    exam_id = request.form.get("exam_id") or f"exam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    title = request.form.get("title", "").strip() or f"Exam {exam_id}"
    created_by = request.form.get("created_by", "Teacher")
    created_at = datetime.datetime.now().isoformat()

    # create folder for exam files
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    os.makedirs(exam_folder, exist_ok=True)

    # collect questions
    questions = []
    # front-end should send question indices in a hidden input 'q_count'
    try:
        q_count = int(request.form.get("q_count", "0"))
    except:
        q_count = 0

    for i in range(1, q_count+1):
        q_prefix = f"q{i}"
        qid = request.form.get(f"{q_prefix}_id") or f"{q_prefix}"
        marks = int(request.form.get(f"{q_prefix}_marks") or 0)
        instruction = request.form.get(f"{q_prefix}_instruction") or ""
        model_answer = request.form.get(f"{q_prefix}_model") or ""

        # save uploaded question image
        qfile = request.files.get(f"{q_prefix}_question")
        q_filename = ""
        if qfile:
            q_filename = secure_filename(qfile.filename)
            if not q_filename:
                q_filename = f"{qid}_question.png"
            qfile.save(os.path.join(exam_folder, q_filename))

        # save uploaded diagram image (optional)
        dfile = request.files.get(f"{q_prefix}_diagram")
        d_filename = ""
        if dfile:
            d_filename = secure_filename(dfile.filename)
            if not d_filename:
                d_filename = f"{qid}_diagram.png"
            dfile.save(os.path.join(exam_folder, d_filename))

        questions.append({
            "qid": qid,
            "marks": marks,
            "instruction": instruction,
            "question_image": q_filename,
            "diagram_image": d_filename,
            "model_answer": model_answer
        })

    exam_json = {
        "exam_id": exam_id,
        "title": title,
        "created_by": created_by,
        "created_at": created_at,
        "questions": questions
    }

    # write json
    with open(os.path.join(exam_folder, "exam.json"), "w", encoding="utf-8") as f:
        json.dump(exam_json, f, indent=2)

    # return preview link
    preview_url = url_for("exam_preview", exam_id=exam_id)
    return f"Exam saved: <a href='{preview_url}' target='_blank'>{preview_url}</a>"

# --- List exams (simple listing) ---
@app.route("/teacher/exams")
def teacher_exams():
    items = []
    for name in os.listdir(EXAMS_DIR):
        path = os.path.join(EXAMS_DIR, name)
        if os.path.isdir(path):
            json_path = os.path.join(path, "exam.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items.append({"exam_id": data.get("exam_id"), "title": data.get("title"), "created_at": data.get("created_at")})
    return render_template("list_exams.html", exams=items)

# --- Serve exam files ---
@app.route("/exam_file/<exam_id>/<filename>")
def exam_file(exam_id, filename):
    return send_from_directory(os.path.join(EXAMS_DIR, exam_id), filename)

# --- Preview exam (student view for the first question for now) ---
@app.route("/exam/preview/<exam_id>")
def exam_preview(exam_id):
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    json_path = os.path.join(exam_folder, "exam.json")
    if not os.path.exists(json_path):
        return "Exam not found", 404
    with open(json_path, "r", encoding="utf-8") as f:
        exam = json.load(f)
    # For preview we'll render first question (extend later to full multi-question UI)
    first_q = exam["questions"][0] if exam["questions"] else None
    return render_template("exam_preview.html", exam=exam, question=first_q, exam_id=exam_id)


# ------------------------------------------------------------------
# Route: start exam -> redirect to first question
# ------------------------------------------------------------------
@app.route("/exam/start/<exam_id>")
def exam_start(exam_id):
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    json_path = os.path.join(exam_folder, "exam.json")
    if not os.path.exists(json_path):
        return "Exam not found", 404
    with open(json_path, "r", encoding="utf-8") as f:
        exam = json.load(f)
    total = len(exam.get("questions", []))
    if total == 0:
        return "No questions in exam", 404
    # redirect to question 1
    return redirect(url_for("exam_question", exam_id=exam_id, qindex=1))

# ------------------------------------------------------------------
# Route: show a question page
# ------------------------------------------------------------------
@app.route("/exam/<exam_id>/q/<int:qindex>")
def exam_question(exam_id, qindex):
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    json_path = os.path.join(exam_folder, "exam.json")
    if not os.path.exists(json_path):
        return "Exam not found", 404
    with open(json_path, "r", encoding="utf-8") as f:
        exam = json.load(f)
    questions = exam.get("questions", [])
    total = len(questions)
    if qindex < 1 or qindex > total:
        return "Question index out of range", 404
    question = questions[qindex-1]
    # construct urls for images served via /exam_file/<exam_id>/<filename>
    return render_template("student_exam.html",
                           exam=exam,
                           exam_id=exam_id,
                           question=question,
                           qindex=qindex,
                           total=total)

# ------------------------------------------------------------------
# Endpoint: autosave per-question (saves drawing + text, returns saved filenames)
# Expects JSON: { exam_id, qindex, studentName, answerText, overlayImage (dataURL) }
# ------------------------------------------------------------------
@app.route("/exam/autosave", methods=["POST"])
def exam_autosave():
    data = request.get_json()
    if not data:
        return jsonify({"status":"error","message":"No JSON received"}), 400

    exam_id = data.get("exam_id")
    qindex = int(data.get("qindex", 0))
    student = data.get("studentName", "").strip().replace(" ", "_")
    answerText = data.get("answerText", "")
    overlayData = data.get("overlayImage")  # data:image/png;base64,...

    if not exam_id or not student or qindex < 1:
        return jsonify({"status":"error","message":"Missing params"}), 400

    # ensure exam exists
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    json_path = os.path.join(exam_folder, "exam.json")
    if not os.path.exists(json_path):
        return jsonify({"status":"error","message":"Exam not found"}), 404
    with open(json_path, "r", encoding="utf-8") as f:
        exam = json.load(f)
    questions = exam.get("questions", [])
    if qindex > len(questions):
        return jsonify({"status":"error","message":"Question index out of range"}), 400

    q = questions[qindex-1]
    qid = q.get("qid", f"q{qindex}")

    # prepare student's attempt folder
    student_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    os.makedirs(student_folder, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    saved_overlay_filename = ""
    if overlayData and overlayData.startswith("data:image"):
        header, b64 = overlayData.split(",",1)
        ext = "png"
        saved_overlay_filename = f"{exam_id}_{student}_{qid}_{timestamp}.{ext}"
        save_path = os.path.join(DRAWINGS_DIR, saved_overlay_filename)
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(b64))

    # Load or create attempt json for this student
    attempt_file = os.path.join(student_folder, f"{student}.json")
    if os.path.exists(attempt_file):
        with open(attempt_file, "r", encoding="utf-8") as f:
            attempt = json.load(f)
    else:
        attempt = {"exam_id": exam_id, "student": student, "answers": {}, "submitted": False, "last_saved": None}

    # save the answer object for this qid
    attempt["answers"][qid] = {
        "qindex": qindex,
        "answerText": answerText,
        "overlay_file": saved_overlay_filename,
        "saved_at": timestamp
    }
    attempt["last_saved"] = timestamp

    # write attempt
    with open(attempt_file, "w", encoding="utf-8") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status":"success", "overlay_file": saved_overlay_filename, "attempt_file": os.path.basename(attempt_file)})

# ------------------------------------------------------------------
# Endpoint: final submit (marks attempt as submitted)
# Expects JSON: { exam_id, studentName }
# ------------------------------------------------------------------
@app.route("/exam/submit", methods=["POST"])
def exam_submit():
    data = request.get_json()
    exam_id = data.get("exam_id")
    student = data.get("studentName", "").strip().replace(" ", "_")
    if not exam_id or not student:
        return jsonify({"status":"error","message":"Missing params"}), 400

    student_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    attempt_file = os.path.join(student_folder, f"{student}.json")
    if not os.path.exists(attempt_file):
        return jsonify({"status":"error","message":"Attempt not found"}), 404

    with open(attempt_file, "r", encoding="utf-8") as f:
        attempt = json.load(f)
    attempt["submitted"] = True
    attempt["submitted_at"] = datetime.datetime.now().isoformat()

    with open(attempt_file, "w", encoding="utf-8") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status":"success", "message":"Submitted"})

# -----------------------------
# Run local
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
