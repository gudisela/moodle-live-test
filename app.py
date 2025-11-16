from flask import Flask, render_template, request
import csv, os, base64, datetime, send_file

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
