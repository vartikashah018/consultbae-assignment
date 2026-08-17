# ConsultBae Data Integration & Automation

A mini data integration, duplicate detection, automation, and audio collection system built for the ConsultBae technical assignment.

The project combines three inconsistent CSV datasets into a single SQLite database, exposes a duplicate-checking API, connects that API to an n8n workflow, and provides a Flask-based audio collection application.

---

## 1. Project Overview

The project covers the following assignment requirements:

- Merge three independent CSV datasets into one clean database.
- Identify the same person across different systems without a common ID.
- Record and handle data-quality issues.
- Build a working n8n low-code automation for duplicate detection.
- Build a mini audio collection application.
- Automatically extract audio metadata.
- Provide a second view for submitted recordings.
- Document data-quality issues and the main debugging/stuck points.

---

# 2. Architecture

```text
                    ┌─────────────────────────┐
                    │       3 CSV FILES       │
                    │                         │
                    │ Naukri Applicants       │
                    │ Gig Workers             │
                    │ CBNexus Contacts        │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Normalize + Validate   │
                    │  + Entity Matching      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        SQLite           │
                    │                         │
                    │ people                  │
                    │ source_records          │
                    │ data_quality_issues     │
                    │ audio_submissions       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌───────────────┐       ┌────────────────┐
             │   Flask API   │       │   Audio App    │
             │               │       │                │
             │ Duplicate     │       │ Upload Audio   │
             │ Detection     │       │ Extract Audio  │
             └───────┬───────┘       │ Metadata       │
                     │               └───────┬────────┘
                     │                       │
                     ▼                       ▼
                ┌───────────┐           SQLite
                │    n8n    │
                │ Automation│
                └───────────┘
 3. Task 1 — Data Merge
Input Data

The project uses three source systems:

data/source1_naukri_applicants.csv
data/source2_gig_workers.csv
data/source3_cbnexus_contacts.csv

Each source has different columns, formatting, and data-quality problems.

The pipeline normalizes the source records before matching them.

Database

SQLite is used for the assignment because it is simple to run locally and does not require a separate database server.

The final ingestion run produced:

103 source records
54 canonical people
3 recorded data-quality issues

Multiple records belonging to the same person are linked to one canonical person record.
4. Entity Matching Strategy

There is no single ID shared across all three systems.

The matching process therefore uses normalized identifying fields.

The matching strategy prioritizes stronger identifiers before weaker ones.

Match 1 — Exact Phone

A normalized phone number match is treated as a strong identifier.

Example:

Varun Jain
→ exact_phone
Match 2 — Exact Email

A normalized email match is also treated as a strong identifier.

Example:

Varun Jain
varun.jain29@example.com
→ exact_email

The Gig Workers dataset contains email addresses that successfully matched existing people using this method.

Match 3 — Exact Name + City

When stronger identifiers are unavailable, normalized name and city are used together.

Examples from the ingestion process include:

Arjun Mehta → exact_name_city
Manish Bhatia → exact_name_city
Divya Chopra → exact_name_city
Karan Chopra → exact_name_city
Vikram Mehta → exact_name_city

The pipeline records the match method and score so that matching decisions remain explainable.

5. Data Normalization

Before matching, fields are normalized.

The pipeline handles issues such as:

Different capitalization.
Leading/trailing whitespace.
Inconsistent city formatting.
Normalized email values.
Normalized phone values.
Normalized person names.

For example:

Pune
PUNE
pune

are normalized so they can be compared consistently.

6. Task 2 — n8n Automation

The n8n workflow is exported to:

n8n/consultbae-duplicate-check.json

An additional workflow file is also included:

n8n/duplicate_alert.json
Workflow

The automation follows this flow:

Incoming CSV
     ↓
Webhook
     ↓
Extract From File
     ↓
Loop Over Items
     ↓
HTTP Request
     ↓
Flask Duplicate API
     ↓
IF duplicate?

The incoming Gig Workers CSV contains fields such as:

email_id
worker_name
rate
location
status
skill_tags

The n8n HTTP Request maps the fields to the API:

worker_name → name
email_id    → email

The request is sent to:

POST /api/check-duplicate

The Flask API checks the same SQLite database used by the data pipeline.

Example

For:

Name:
Varun Jain


Email:
varun.jain29@example.com

the API returns a duplicate result using exact email matching.

Example:

{
  "duplicate": true,
  "match": {
    "city": "pune",
    "email": "varun.jain29@example.com",
    "name": "varun jain",
    "person_id": 18,
    "phone": "9000000263"
  },
  "match_method": "exact_email"
}

This demonstrates that n8n is connected to the application's duplicate detection API instead of implementing the matching logic again inside n8n.

7. Task 3 — Mini Audio Collection App

The audio application is built using Flask.

The application allows a user to:

Enter their name.
Enter their phone number.
Upload an audio file.
Submit the recording.
View previously submitted recordings.
Running the App

Activate the virtual environment:

source venv/bin/activate

Start Flask:

python app/app.py

The application runs at:

http://127.0.0.1:5001

The submissions page is:

http://127.0.0.1:5001/submissions
8. Audio Metadata

For every submitted audio recording, the application automatically extracts and stores:

Duration
Sample rate
Bitrate
Loudness
Rough noise/quality estimate

Example test recording:

Duration: 12.445896 seconds
Sample rate: 44100 Hz
Bitrate: 66819 bps
Loudness: -39.54 dB
Noise estimate: acceptable

The extracted properties are displayed in the submissions view along with an audio player.

9. API

The duplicate-check API is:

POST http://127.0.0.1:5001/api/check-duplicate

Example:

curl -i -X POST http://127.0.0.1:5001/api/check-duplicate \
-H "Content-Type: application/json" \
-d '{"name":"Varun Jain","email":"varun.jain29@example.com"}'

Expected result:

{
  "duplicate": true,
  "match_method": "exact_email"
}

The API can also use phone information when supplied.

10. Task 4 — Data Quality Issues Report

The source files intentionally contain imperfect data.

The ingestion pipeline records detected problems in the data_quality_issues table.

Three issues were recorded.

Issue 1 — Empty Row

Source:

gig_workers

Record:

10

Problem:

The entire row was empty.

Action:

Skipped during ingestion.

Severity:

Low
Issue 2 — Malformed Row

Source:

gig_workers

Record:

18

Problem:

The email column contained skill tags and the remaining fields were shifted.

Action:

The fields were reconstructed based on the expected row structure.

Severity:

High

This was treated as a structural data-quality problem rather than allowing the malformed row to silently create incorrect database fields.

Issue 3 — Embedded Header

Source:

cbnexus

Record:

14

Problem:

A header row appeared inside the data.

Action:

The embedded header row was skipped during ingestion.

Severity:

Medium
11. Project Structure
consultbae-assignment/
│
├── app/
│   ├── app.py
│   ├── audio.py
│   ├── test_audio.py
│   ├── static/
│   └── templates/
│       ├── index.html
│       └── submissions.html
│
├── data/
│   ├── source1_naukri_applicants.csv
│   ├── source2_gig_workers.csv
│   ├── source3_cbnexus_contacts.csv
│   └── test_incoming.csv
│
├── database/
│   ├── create_database.py
│   └── schema.sql
│
├── pipeline/
│   ├── database.py
│   ├── ingest.py
│   ├── matching.py
│   ├── normalize.py
│   ├── test_matching.py
│   └── test_normalize.py
│
├── n8n/
│   ├── consultbae-duplicate-check.json
│   └── duplicate_alert.json
│
├── create_database.py
├── data_quality_check.py
├── inspect_data.py
├── requirements.txt
├── README.md
└── .gitignore
12. Setup
Clone
git clone <YOUR_GITHUB_REPO_URL>
cd consultbae-assignment
Create virtual environment
python3 -m venv venv
source venv/bin/activate
Install dependencies
pip install -r requirements.txt
Create database
python database/create_database.py
Run ingestion
python pipeline/ingest.py

The ingestion process reads all three CSV files, normalizes the data, records data-quality issues, performs entity matching, and stores the result in SQLite.

13. Running Flask
source venv/bin/activate
python app/app.py

Open:

http://127.0.0.1:5001
14. Running n8n

n8n is run locally.

Node.js 22 is used.

If required:

nvm use --delete-prefix v22.23.2

Then:

npx n8n

Open:

http://localhost:5678

The Flask API must also be running on port 5001 because the n8n HTTP Request node calls:

http://127.0.0.1:5001/api/check-duplicate

The workflow can be imported from:

n8n/consultbae-duplicate-check.json
15. Testing

Audio functionality:

python app/test_audio.py

Normalization tests:

python pipeline/test_normalize.py

Matching tests:

python pipeline/test_matching.py

Duplicate API:

curl -i -X POST http://127.0.0.1:5001/api/check-duplicate \
-H "Content-Type: application/json" \
-d '{"name":"Varun Jain","email":"varun.jain29@example.com"}'
16. Stuck Log

The following are the main places where I got stuck and how I resolved them.

Stuck 1 — Flask API was not reachable
Problem

While testing the API, curl returned:

curl: (7) Failed to connect to 127.0.0.1 port 5001
Investigation

The virtual environment was activated, but Flask itself was not running.

Activating:

source venv/bin/activate

does not start the application.

Solution

I started Flask explicitly:

python app/app.py

and verified:

Running on http://127.0.0.1:5001

I then tested the API again with curl.

What I learned

The environment and the application server are separate processes, so I kept Flask running in one terminal while testing from another.

Stuck 2 — Port conflict / unexpected 403
Problem

A request intended for the Flask API returned:

HTTP/1.1 403 Forbidden
Server: AirTunes
Investigation

The response headers showed that the request was not reaching the Flask development server.

Solution

I moved the Flask application to port 5001 and verified the server using Werkzeug response headers.

After that:

POST http://127.0.0.1:5001/api/check-duplicate

returned:

HTTP/1.1 200 OK
Server: Werkzeug
Why I chose this solution

I did not want to modify or disable an unrelated system service. Changing the development port was the smallest and safest fix.

Stuck 3 — n8n Webhook response error
Problem

The n8n webhook produced:

No Respond to Webhook node found in the workflow
Investigation

The Webhook node was configured to use a Respond to Webhook node, but the workflow did not contain one.

Solution

I changed the webhook response behavior to respond immediately.

The webhook then successfully accepted the incoming CSV.

What I learned

The Webhook response configuration must match the actual nodes present in the workflow.

17. Additional n8n Debugging

During testing, the workflow processed the CSV through the Extract From File and Loop Over Items nodes.

One problem encountered was excessive requests being sent to the API.

The workflow was adjusted so that records are handled through the loop rather than sending all records as one uncontrolled burst.

This was important because the duplicate-check API is intended to receive one applicant record at a time.

18. Stretch Task — 5,000 Workers

If the audio application were launched to 5,000 gig workers over a weekend, the current local architecture would not be sufficient for production.

What would break first?
Local audio storage

Thousands of audio files could quickly consume local disk space.

A production system should use object storage instead of storing files on the application server.

SQLite concurrency

SQLite is suitable for this assignment, but a larger production workload would be better served by PostgreSQL.

Upload size and failures

Large or corrupt uploads could consume resources or fail during processing.

I would add:

Maximum upload size.
MIME/type validation.
Upload timeouts.
Retry handling.
Explicit processing states.

For example:

uploaded
   ↓
processing
   ↓
processed

or:

processing
   ↓
failed
Audio processing

Audio metadata extraction should move to background workers so the web request does not remain blocked while processing files.

Duplicate submissions

Workers may submit the same recording multiple times.

I would use an idempotency key and/or audio content hash to detect repeated uploads.

19. Production Architecture

A scalable version could look like:

Workers
   ↓
Load Balancer
   ↓
Application Servers
   ↓
Object Storage
   ↓
Message Queue
   ↓
Audio Processing Workers
   ↓
PostgreSQL

This would separate:

Web traffic
File storage
Background processing
Database operations

and make the system easier to scale horizontally.

20. Limitations

This project is intentionally designed as a local assignment implementation.

Current limitations include:

Flask is run locally.
SQLite is used instead of PostgreSQL.
Audio files are stored locally.
n8n is self-hosted locally.
Authentication is not implemented.
Authorization is not implemented.
Audio processing is not queue-based.
The n8n workflow is intended for demonstration rather than production-scale processing.

These choices prioritize demonstrating the required end-to-end functionality while keeping the project simple to run and inspect.

21. Demo Flow

For the screen recording, the intended demonstration is:

1. Show the three CSV files
        ↓
2. Run the ingestion pipeline
        ↓
3. Show the merged database result
        ↓
4. Explain matching logic
        ↓
5. Open n8n
        ↓
6. Send a CSV through the webhook
        ↓
7. Show duplicate detection
        ↓
8. Open the audio application
        ↓
9. Upload an audio recording
        ↓
10. Show extracted metadata
        ↓
11. Open the submissions page
        ↓
12. Play the recording
        ↓
13. Explain the hardest debugging decisions
22. Git History

The repository contains incremental commits showing the development process.

Current major commits include:

3fc7a3e  feat: add merged database and duplicate detection API
6dec62a  Add audio collection and metadata extraction
3d7b3bf  Build CSV ingestion and entity matching pipeline

The history shows the project evolving from the data ingestion and entity matching pipeline into the API, automation, and application components.

23. Technologies
Python 3
Flask
SQLite
n8n
HTML
CSS
JavaScript
CSV
Git
GitHub
Audio metadata processing
24. Author

Built as part of the ConsultBae technical assignment.



After pasting it, run:


```bash
git add README.md
git commit -m "docs: complete assignment README"
git push origin main

Then verify:

git status

You want:

nothing to commit, working tree clean