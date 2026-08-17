import sqlite3
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

from audio import get_audio_metadata


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "consultbae.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"

ALLOWED_EXTENSIONS = {
    "mp3",
    "wav",
    "m4a",
    "aac",
    "ogg",
    "flac",
}


app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_FOLDER.mkdir(exist_ok=True)


def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def allowed_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS


def find_or_create_person(name, phone):
    """
    Find an existing person using normalized phone.

    If no person exists, create a new master person.
    """

    connection = get_db()

    clean_name = " ".join(name.strip().lower().split())

    digits = "".join(
        character
        for character in phone
        if character.isdigit()
    )

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    # First try exact phone match.
    person = connection.execute(
        """
        SELECT *
        FROM people
        WHERE phone = ?
        """,
        (digits,),
    ).fetchone()

    if person:
        connection.close()
        return person["id"]

    # No phone match: create a new person.
    cursor = connection.execute(
        """
        INSERT INTO people (
            canonical_name,
            phone
        )
        VALUES (?, ?)
        """,
        (
            clean_name,
            digits,
        ),
    )

    connection.commit()

    person_id = cursor.lastrowid

    connection.close()

    return person_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    audio_file = request.files.get("audio")

    if not name or not phone:
        return "Name and phone number are required.", 400

    if not audio_file or audio_file.filename == "":
        return "Please select an audio file.", 400

    if not allowed_file(audio_file.filename):
        return "Unsupported audio format.", 400

    person_id = find_or_create_person(
        name,
        phone,
    )

    filename = secure_filename(
        audio_file.filename
    )

    # Prevent filename collisions.
    import uuid

    unique_filename = (
        f"{uuid.uuid4().hex}_{filename}"
    )

    file_path = (
        UPLOAD_FOLDER /
        unique_filename
    )

    audio_file.save(file_path)

    try:
        metadata = get_audio_metadata(
            file_path
        )

    except Exception as error:

        if file_path.exists():
            file_path.unlink()

        return (
            f"Could not process audio: {error}",
            500,
        )

    connection = get_db()

    connection.execute(
        """
        INSERT INTO audio_submissions (
            person_id,
            file_name,
            file_path,
            duration_seconds,
            sample_rate_hz,
            bitrate_bps,
            loudness_db,
            noise_estimate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            person_id,
            filename,
            str(
                file_path.relative_to(BASE_DIR)
            ),
            metadata["duration_seconds"],
            metadata["sample_rate_hz"],
            metadata["bitrate_bps"],
            metadata["loudness_db"],
            metadata["noise_estimate"],
        ),
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("submissions")
    )


@app.route("/submissions")
def submissions():

    connection = get_db()

    rows = connection.execute(
        """
        SELECT
            audio_submissions.*,
            people.canonical_name,
            people.phone
        FROM audio_submissions
        JOIN people
            ON people.id = audio_submissions.person_id
        ORDER BY audio_submissions.created_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "submissions.html",
        submissions=rows,
    )


@app.route("/audio/<int:submission_id>")
def serve_audio(submission_id):

    connection = get_db()

    row = connection.execute(
        """
        SELECT file_path
        FROM audio_submissions
        WHERE id = ?
        """,
        (submission_id,),
    ).fetchone()

    connection.close()

    if not row:
        return "Audio not found.", 404

    file_path = BASE_DIR / row["file_path"]

    if not file_path.exists():
        return "Audio file is missing.", 404

    from flask import send_file

    return send_file(
        file_path,
        conditional=True,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )