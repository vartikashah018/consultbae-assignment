import sqlite3
import uuid
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    jsonify,
)
from werkzeug.utils import secure_filename

from audio import get_audio_metadata


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "consultbae.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"


# ============================================================
# Configuration
# ============================================================

ALLOWED_EXTENSIONS = {
    "mp3",
    "wav",
    "m4a",
    "aac",
    "ogg",
    "flac",
}

MAX_FILE_SIZE = 50 * 1024 * 1024


app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

UPLOAD_FOLDER.mkdir(exist_ok=True)


# ============================================================
# Database
# ============================================================

def get_db():
    """
    Create a SQLite connection.

    Row factory allows us to access columns using names.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# Helpers
# ============================================================

def normalize_phone(phone):
    """
    Normalize an Indian phone number.

    Examples:

    +91-9000000131
    919000000131
    9000000131

    become:

    9000000131
    """

    if not phone:
        return ""

    digits = "".join(
        character
        for character in str(phone)
        if character.isdigit()
    )

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    return digits


def normalize_name(name):
    """
    Normalize whitespace and capitalization.
    """

    if not name:
        return ""

    return " ".join(
        str(name).strip().lower().split()
    )


def normalize_email(email):
    """
    Normalize an email address.
    """

    if not email:
        return ""

    return str(email).strip().lower()


def allowed_file(filename):
    """
    Check whether the uploaded file extension is supported.
    """

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# Person lookup / creation
# ============================================================

def find_or_create_person(name, phone):
    """
    Find a person using phone number.

    If the phone does not exist, create a new person.
    """

    normalized_name = normalize_name(name)
    normalized_phone = normalize_phone(phone)

    connection = get_db()

    # --------------------------------------------------------
    # First: exact phone match
    # --------------------------------------------------------

    if normalized_phone:

        person = connection.execute(
            """
            SELECT *
            FROM people
            WHERE phone = ?
            LIMIT 1
            """,
            (normalized_phone,),
        ).fetchone()

        if person:

            # Fill in missing name if necessary.
            if not person["canonical_name"] and normalized_name:

                connection.execute(
                    """
                    UPDATE people
                    SET canonical_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        normalized_name,
                        person["id"],
                    ),
                )

                connection.commit()

            connection.close()

            return person["id"]

    # --------------------------------------------------------
    # No match: create person
    # --------------------------------------------------------

    cursor = connection.execute(
        """
        INSERT INTO people (
            canonical_name,
            phone
        )
        VALUES (?, ?)
        """,
        (
            normalized_name,
            normalized_phone,
        ),
    )

    connection.commit()

    person_id = cursor.lastrowid

    connection.close()

    return person_id


# ============================================================
# Home page
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# Audio submission
# ============================================================

@app.route("/submit", methods=["POST"])
def submit():

    name = request.form.get(
        "name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    audio_file = request.files.get(
        "audio"
    )

    # --------------------------------------------------------
    # Validate person information
    # --------------------------------------------------------

    if not name:
        return "Name is required.", 400

    if not phone:
        return "Phone number is required.", 400

    # --------------------------------------------------------
    # Validate audio
    # --------------------------------------------------------

    if not audio_file:
        return "Please select an audio file.", 400

    if not audio_file.filename:
        return "Please select an audio file.", 400

    if not allowed_file(audio_file.filename):
        return (
            "Unsupported audio format. "
            "Use MP3, WAV, M4A, AAC, OGG or FLAC.",
            400,
        )

    # --------------------------------------------------------
    # Find/create person
    # --------------------------------------------------------

    person_id = find_or_create_person(
        name,
        phone,
    )

    # --------------------------------------------------------
    # Create unique filename
    # --------------------------------------------------------

    original_filename = secure_filename(
        audio_file.filename
    )

    unique_filename = (
        f"{uuid.uuid4().hex}_"
        f"{original_filename}"
    )

    file_path = (
        UPLOAD_FOLDER /
        unique_filename
    )

    # --------------------------------------------------------
    # Save uploaded audio
    # --------------------------------------------------------

    audio_file.save(
        file_path
    )

    # --------------------------------------------------------
    # Extract audio metadata
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Store submission
    # --------------------------------------------------------

    connection = get_db()

    relative_path = str(
        file_path.relative_to(BASE_DIR)
    )

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
            original_filename,
            relative_path,
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


# ============================================================
# Submissions page
# ============================================================

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


# ============================================================
# Serve audio
# ============================================================

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

    file_path = (
        BASE_DIR /
        row["file_path"]
    )

    if not file_path.exists():
        return "Audio file is missing.", 404

    return send_file(
        file_path,
        conditional=True,
    )


# ============================================================
# n8n Duplicate Check API
# ============================================================

@app.route(
    "/api/check-duplicate",
    methods=["POST"]
)
def check_duplicate():

    data = request.get_json(
        silent=True
    ) or {}

    name = normalize_name(
        data.get("name", "")
    )

    email = normalize_email(
        data.get("email", "")
    )

    phone = normalize_phone(
        data.get("phone", "")
    )

    connection = get_db()

    person = None
    match_method = None

    # --------------------------------------------------------
    # 1. Exact phone
    # --------------------------------------------------------

    if phone:

        person = connection.execute(
            """
            SELECT
                id,
                canonical_name,
                email,
                phone,
                city
            FROM people
            WHERE phone = ?
            LIMIT 1
            """,
            (phone,),
        ).fetchone()

        if person:
            match_method = "exact_phone"

    # --------------------------------------------------------
    # 2. Exact email
    # --------------------------------------------------------

    if person is None and email:

        person = connection.execute(
            """
            SELECT
                id,
                canonical_name,
                email,
                phone,
                city
            FROM people
            WHERE LOWER(email) = ?
            LIMIT 1
            """,
            (email,),
        ).fetchone()

        if person:
            match_method = "exact_email"

    # --------------------------------------------------------
    # 3. Exact normalized name
    # --------------------------------------------------------

    if person is None and name:

        person = connection.execute(
            """
            SELECT
                id,
                canonical_name,
                email,
                phone,
                city
            FROM people
            WHERE LOWER(canonical_name) = ?
            LIMIT 1
            """,
            (name,),
        ).fetchone()

        if person:
            match_method = "exact_name"

    connection.close()

    # --------------------------------------------------------
    # Duplicate found
    # --------------------------------------------------------

    if person:

        return jsonify(
            {
                "duplicate": True,
                "match_method": match_method,
                "match": {
                    "person_id": person["id"],
                    "name": person["canonical_name"],
                    "email": person["email"],
                    "phone": person["phone"],
                    "city": person["city"],
                },
            }
        )

    # --------------------------------------------------------
    # No duplicate
    # --------------------------------------------------------

    return jsonify(
        {
            "duplicate": False,
            "match_method": None,
            "match": None,
        }
    )


# ============================================================
# Health check
# ============================================================

@app.route("/health")
def health():

    return jsonify(
        {
            "status": "ok"
        }
    )


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5001,
    )