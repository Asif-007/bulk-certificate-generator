# Bulk Certificate Generator

A FastAPI backend that accepts bulk certificate-generation requests, validates recipient information, generates individual PDF certificates, tracks job progress, and exposes endpoints to retrieve generated certificates.

## Features

- **Bulk requests:** Submit certificate details and multiple recipients in one API request.
- **Input validation:** Validate request fields, email addresses, dates, and recipient counts.
- **Individual PDF certificates:** Generate a separate PDF for each recipient using ReportLab.
- **Job tracking:** Track processing status, total recipients, successful generations, failures, and progress percentage.
- **Failure isolation:** A certificate-generation failure for one recipient does not stop processing other recipients.
- **Certificate retrieval:** Download a generated PDF using its job and recipient IDs.
- **Persistent records:** Store jobs and recipient outcomes in SQLite using SQLAlchemy.
- **PDF student import:** Parse a text-based `Name | Email` student list into an editable, validated preview.
- **Theme support:** Switch between light and dark themes with a persisted preference.
- **Automated tests:** Test API validation, job processing, progress, failure handling, and downloads.

## Technology Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- ReportLab
- Pydantic
- pytest
- HTTPX
- pdfplumber
- python-multipart

## Prerequisites

- Python 3.12 or later recommended
- Git

The project has been developed and tested in a Python 3.14 virtual environment.

## Local Setup

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/Asif-007/bulk-certificate-generator.git
cd bulk-certificate-generator
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Running the Backend

Start the development server from the project root:

```powershell
python -m uvicorn app.main:app --reload
```

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive Swagger documentation: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/health`

The SQLite database is created locally as `certificate_generator.db`. Generated PDF files are stored in `generated_certificates/`.

## Running the Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend defaults
to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` in `frontend/.env` to use
another backend. The API explicitly allows the two local Vite origins.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API availability |
| POST | `/validate-request` | Validate and inspect a certificate request |
| POST | `/import-students-pdf` | Parse and validate an uploaded student-list PDF without creating a job |
| POST | `/jobs` | Create a bulk generation job |
| GET | `/jobs/{job_id}` | Retrieve job status, progress, and recipient outcomes |
| GET | `/jobs/{job_id}/recipients/{recipient_id}/certificate` | Download a generated certificate |

### Create a generation job

Send a `POST` request to `/jobs` with a JSON body:

```json
{
  "certificate": {
    "course_name": "Python Programming",
    "issuer": "ABC Institute",
    "completion_date": "2026-10-10"
  },
  "recipients": [
    {
      "name": "Asif",
      "email": "asif@example.com"
    },
    {
      "name": "Rahul",
      "email": "rahul@example.com"
    }
  ]
}
```

A successful request returns HTTP `202 Accepted` with the job ID and initial status.

### Import students from a PDF

Send a multipart `POST` request to `/import-students-pdf` with a field named
`file`. The upload must be a real PDF (the server checks both the declared
content type and `%PDF-` signature), must be non-empty, and must be no larger
than 10 MB. The endpoint only parses and validates; it never creates a
generation job.

The supported layout is a text-based table with a recognizable header row:

```text
Name | Email
Asif Khan | asif@example.com
Rahul Das | rahul@example.com
```

`Full Name`, `Student Name`, and `Email Address` are also recognized. Pipe,
comma, tab-separated, and extracted table columns are supported. Multiple
pages are supported. The response contains `rows` with stable `row_id` values,
normalized `name` and `email` values, row-specific `errors`, and a
`duplicate` flag. Its `summary` reports `total_candidates`, `valid_count`,
`invalid_count`, `duplicate_count`, and `requires_correction`.

Missing names, malformed emails, names over 100 characters, and
case-insensitive duplicate emails are reported rather than silently dropped.
The frontend lets users edit or remove rows and must receive an explicit
confirmation before submitting the corrected list through the existing `/jobs`
endpoint. The server remains authoritative and revalidates the final request.

Scanned/image-only PDFs, arbitrary prose, password-protected PDFs, corrupted
files, and PDFs without a supported table header are not supported. OCR is
intentionally out of scope; use a text-based PDF export instead.

### Check job progress

Use the returned job ID:

```text
GET /jobs/{job_id}
```

The response includes:

- Job status
- Total, successful, and failed recipient counts
- Processed recipient count
- Progress percentage
- Individual recipient outcomes
- Certificate download URLs for successful recipients

### Download a certificate

Use the job ID and recipient ID from the status response:

```text
GET /jobs/{job_id}/recipients/{recipient_id}/certificate
```

A successful request returns a PDF file. Missing jobs, mismatched job-recipient IDs, and unavailable certificates return HTTP `404 Not Found`.

## Processing and Failure Handling

The API uses FastAPI `BackgroundTasks` to process certificate-generation jobs after accepting the request.

Each recipient is processed independently. Successful generations store the certificate file path, while failures record an error message and update the failure count.

The job status is finalized as:

- `completed`: All recipients succeeded.
- `partially_failed`: Some recipients succeeded and some failed.
- `failed`: No recipients succeeded.

Progress is calculated from the number of successful and failed recipients relative to the total recipient count.

**Limitation:** FastAPI `BackgroundTasks` is not a durable job queue. If the application process stops unexpectedly, in-progress work is not guaranteed to resume automatically. A production deployment could use a durable worker system such as Celery with a message broker.

## Database Design

The application uses two relational tables:

### `generation_jobs`

Stores the shared certificate information, job status, creation timestamp, recipient totals, success count, and failure count.

### `recipient_results`

Stores each recipient's name, email, processing status, generated file path, and any error message. Each record references its parent job through `job_id`.

This structure allows job-level progress tracking while preserving the outcome of each recipient separately.

## Running Automated Tests

Run the complete test suite from the project root:

```bash
python -m pytest -v
```

The test suite covers:

- Health endpoint behavior
- Invalid email and empty recipient-list validation
- Job creation and processing
- Progress and recipient status tracking
- Certificate downloads
- Individual-recipient failure isolation
- Nonexistent job handling
- Mismatched job and recipient handling
- Student-list PDF extraction, validation, duplicate detection, and upload limits

Tests use a temporary SQLite database to isolate test data from the development database.

## Project Structure

```text
bulk-certificate-generator/
├── app/
│   ├── main.py          # API routes and job processing
│   ├── pdf_import.py    # Safe text-based student PDF parsing
│   ├── database.py      # Database engine and sessions
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic request validation
│   └── certificates.py  # PDF certificate generation
├── tests/
│   └── test_api.py      # Automated API tests
├── frontend/
│   ├── src/             # React form, polling, results, and styles
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
├── generated_certificates/
├── certificate_generator.db
├── requirements.txt
├── .gitignore
└── README.md
```

The database and generated certificates are local runtime artifacts and are excluded from version control.

## Using the Complete Application

1. Start the backend and frontend in separate PowerShell terminals.
2. Enter the course details and at least one recipient, adding rows as needed.
3. Select **Generate certificates**.
4. The results card polls while the job is pending or processing and displays
   progress, counts, and each recipient outcome.
5. Select **Download PDF** for successful recipients. Failed recipients show
   their backend error while other recipients continue processing.
6. Select **Start another job** after a terminal result to begin again.

To use PDF import, choose **Upload student PDF**, drop or browse for a PDF,
review the extraction summary, correct or remove invalid rows, check the
confirmation box, and then select **Confirm and generate certificates**.
Switching between input modes preserves the manual rows and imported preview
data rather than silently discarding either list. Use the theme button in the
header to switch between light and dark mode; the selection is stored in
browser local storage.

The frontend handles client-side required-field and email validation plus
backend `422`, `404`, `5xx`, and network errors. Run its production check with
`npm run build` from `frontend`; no separate lint or type-check script is
configured for this small JavaScript application.

## Design Decisions and Limitations

- Native `fetch` is used to keep dependencies minimal. Polling runs every 1.5
  seconds only for non-terminal jobs, prevents overlapping requests, and is
  cleaned up when polling stops.
- The API remains the source of truth. The browser downloads the actual PDF
  returned by the backend and never fabricates successful results.
- FastAPI `BackgroundTasks` is not a durable job queue. In-progress work is
  not guaranteed to resume after a process crash. A production deployment
  would use a durable worker system such as Celery with a message broker.
- Authentication, deployment infrastructure, and durable queues are outside
  this assignment's scope.

## Full-Stack Verification

From the project root:

```powershell
python -m pytest -v
```

From `frontend`:

```powershell
npm install
npm run build
```

The backend tests cover validation, job processing, progress, failure
isolation, 404 handling, and real PDF downloads. The frontend build verifies
the production bundle. With both servers running, manually exercise valid
submission, polling, partial failure, and PDF download flows.

## Current Scope

This repository contains the FastAPI backend and a separate React/Vite
frontend. The API can also be explored through Swagger UI.

The application is intended as a simple bulk certificate-generation assignment and development project, not a production-hardened distributed job-processing service.
