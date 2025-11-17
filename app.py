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

# create folders if not exist
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)
os.makedirs(DIAGRAM_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)

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
# Run local
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
