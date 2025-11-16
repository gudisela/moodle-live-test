from flask import Flask, render_template, request, send_file, url_for
import csv
import os
import base64
import datetime


app = Flask(__name__)

SUBMISSIONS_DIR = "submissions"
if not os.path.exists(SUBMISSIONS_DIR):
    os.makedirs(SUBMISSIONS_DIR)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_name = request.form["student_name"]
        answer_text = request.form["answer_text"]
        drawing_data = request.form["drawing_data"]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{student_name}_{timestamp}".replace(" ", "_")

        # Save answer text to CSV
        with open(f"{SUBMISSIONS_DIR}/answers.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, student_name, answer_text])

        # Save drawing image
        if drawing_data and drawing_data.startswith("data:image/png;base64,"):
            img_data = drawing_data.split(",")[1]
            img_bytes = base64.b64decode(img_data)
            with open(f"{SUBMISSIONS_DIR}/{filename_base}.png", "wb") as img_file:
                img_file.write(img_bytes)

        return "Submission received!"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

@app.route("/diagram/<diagram_filename>")
def diagram_page(diagram_filename):
    return render_template(
        "draw_diagram.html",
        diagram_filename=diagram_filename,
        submit_url=url_for("submit_diagram", diagram_filename=diagram_filename)
    )


@app.route("/submit_diagram/<diagram_filename>", methods=["POST"])
def submit_diagram(diagram_filename):
    import base64

    data = request.get_json()
    img_data = data["image"].split(",")[1]
    img_bytes = base64.b64decode(img_data)

    # Save in submissions folder
    save_path = f"submissions/{diagram_filename}_drawing.png"
    with open(save_path, "wb") as f:
        f.write(img_bytes)

    return {"status": "ok"}
@app.route('/submissions')
def list_submissions():
    files = os.listdir('submissions')
    return render_template('submissions.html', files=files)
@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = os.path.join('submissions', filename)
    return send_file(file_path, as_attachment=True)

from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import base64
from datetime import datetime

# --- Ensure directory exists for diagram overlays ---
DIAGRAM_FOLDER = "diagrams"
OVERLAY_FOLDER = "diagram_overlays"

os.makedirs(DIAGRAM_FOLDER, exist_ok=True)
os.makedirs(OVERLAY_FOLDER, exist_ok=True)

# ----------------------------
# 1. Serve background diagram
# ----------------------------
@app.route("/get_diagram/<filename>")
def get_diagram(filename):
    return send_from_directory(DIAGRAM_FOLDER, filename)

# ----------------------------
# 2. Serve saved overlay drawing
# ----------------------------
@app.route("/get_overlay/<filename>")
def get_overlay(filename):
    return send_from_directory(OVERLAY_FOLDER, filename)

# ----------------------------------------------------
# 3. Load the diagram drawing page with canvas overlay
# ----------------------------------------------------
@app.route("/diagram/<diagram_name>")
def diagram(diagram_name):
    """
    diagram_name = filename of the PNG/JPG diagram stored in /diagrams
    Example: /diagram/physics_light_q4.png
    """
    return render_template("diagram.html", diagram_name=diagram_name)

# ----------------------------------------------------
# 4. Save the student's overlay drawing
# ----------------------------------------------------
@app.route("/save_diagram", methods=["POST"])
def save_diagram():
    """
    Receives JSON:
    {
        "imageData": "data:image/png;base64,iVBORw0KGgoAAA...",
        "sourceDiagram": "physics_light_q4.png"
    }
    """
    data = request.json
    image_data = data.get("imageData")
    diagram_name = data.get("sourceDiagram")

    if not image_data:
        return jsonify({"status": "error", "message": "No image data received"}), 400

    # Remove base64 prefix
    image_base64 = image_data.split(",")[1]

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"overlay_{diagram_name}_{timestamp}.png"
    filepath = os.path.join(OVERLAY_FOLDER, filename)

    # Save file
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(image_base64))

    return jsonify({"status": "success", "file": filename})

