from flask import Flask, render_template, request, send_file, send_from_directory, url_for, jsonify
import os
import csv
import base64
import datetime

app = Flask(__name__)

# -----------------------------
# 0. Directories
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUBMISSIONS_DIR = os.path.join(BASE_DIR, "submissions")
DIAGRAM_FOLDER = os.path.join(BASE_DIR, "diagrams")
OVERLAY_FOLDER = os.path.join(BASE_DIR, "diagram_overlays")

os.makedirs(SUBMISSIONS_DIR, exist_ok=True)
os.makedirs(DIAGRAM_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)

# -----------------------------
# 1. Main text + drawing submission (Phase 1)
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_name = request.form["student_name"]
        answer_text = request.form["answer_text"]
        drawing_data = request.form["drawing_data"]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{student_name}_{timestamp}".replace(" ", "_")

        # Save text
        with open(os.path.join(SUBMISSIONS_DIR, "answers.csv"), "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, student_name, answer_text])

        # Save drawing
        if drawing_data.startswith("data:image/png;base64,"):
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
# 3. Serve background diagram
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
    """
    return render_template("diagram.html", diagram_name=diagram_name)

# -----------------------------
# 6. Save overlay drawing
# -----------------------------
@app.route("/save_diagram", methods=["POST"])
def save_diagram():
    data = request.json
    image_data = data.get("imageData")
    diagram_name = data.get("sourceDiagram")

    if not image_data:
        return jsonify({"status": "error", "message": "No image data received"}), 400

    img_base64 = image_data.split(",")[1]

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"overlay_{diagram_name}_{timestamp}.png"
    filepath = os.path.join(OVERLAY_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(img_base64))

    return jsonify({"status": "success", "file": filename})

# -----------------------------
# 7. Run local
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
