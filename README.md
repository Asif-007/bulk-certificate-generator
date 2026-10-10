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

## Prerequisites

- Python 3.12 or later recommended
- Git

The project has been developed and tested in a Python 3.14 virtual environment.

## Local Setup

Clone the repository and enter the project directory:

```bash
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

```bash
python -m pip install -r requirements.txt
```

## Running the Application

Start the development server from the project root:

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive Swagger documentation: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/health`

The SQLite database is created locally as `certificate_generator.db`. Generated PDF files are stored in `generated_certificates/`.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API availability |
| POST | `/validate-request` | Validate and inspect a certificate request |
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

Tests use a temporary SQLite database to isolate test data from the development database.

## Project Structure

```text
bulk-certificate-generator/
├── app/
│   ├── main.py          # API routes and job processing
│   ├── database.py      # Database engine and sessions
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic request validation
│   └── certificates.py  # PDF certificate generation
├── tests/
│   └── test_api.py      # Automated API tests
├── generated_certificates/
├── certificate_generator.db
├── requirements.txt
├── .gitignore
└── README.md
```

The database and generated certificates are local runtime artifacts and are excluded from version control.

## Current Scope

This repository implements the backend API. A frontend has not yet been added. The API can currently be explored and tested through Swagger UI.

The application is intended as a simple bulk certificate-generation assignment and development project, not a production-hardened distributed job-processing service.
