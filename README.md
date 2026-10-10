# Bulk Certificate Generator

A full-stack application for generating individual PDF certificates in bulk. Institutes can enter student details manually or upload a text-based PDF containing a student list. The application validates recipient information, generates certificates, tracks processing progress, and provides individual PDF downloads.

## Features

- Manual entry of course information and multiple recipients.
- Bulk student import from text-based PDFs.
- Validation of student names, email addresses, and duplicate records.
- Editable preview of imported student records before submission.
- Individual PDF certificate generation using ReportLab.
- Job status and progress tracking.
- Recipient-level success and failure reporting.
- Certificate downloads through the API.
- Responsive React frontend with dark and light themes.
- Automated backend tests using pytest.

## Technology Stack

**Backend**
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- ReportLab
- pdfplumber
- python-multipart

**Frontend**
- React
- Vite
- JavaScript
- CSS

**Testing**
- pytest
- HTTPX

## Project Structure

```text
bulk-certificate-generator/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── models.py
│   ├── database.py
│   ├── certificates.py
│   └── pdf_import.py
├── tests/
│   └── test_api.py
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── generated_certificates/
├── certificate_generator.db
├── requirements.txt
├── .gitignore
└── README.md
```

The SQLite database and generated certificate directory are created locally when the application runs. Runtime artifacts are excluded from version control.

## Prerequisites

- Python 3.12 or later recommended.
- Node.js and npm.
- Git.

The project has been developed and tested using Python 3.14.5.

## 1. Clone the Repository

```bash
git clone https://github.com/Asif-007/bulk-certificate-generator.git
cd bulk-certificate-generator
```

## 2. Set Up the Backend

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install -r requirements.txt
```

## 3. Set Up the Frontend

Open a separate terminal at the project root:

```powershell
cd frontend
npm install
```

If `frontend/.env.example` is provided, copy it to `.env` and adjust the API URL if necessary:

```powershell
Copy-Item .env.example .env
```

The default local backend URL is:

```text
http://127.0.0.1:8000
```

The frontend uses the `VITE_API_BASE_URL` environment variable for API configuration, if configured in the application.

## 4. Run the Application

### Start the backend

From the project root, with the virtual environment activated:

```powershell
python -m uvicorn app.main:app --reload
```

The backend is available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Start the frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open the local URL printed by Vite, normally:

`http://localhost:5173`

Both servers must be running to use the complete application.

## 5. Submit a Certificate Generation Request

The frontend provides two ways to supply recipients.

### Option A: Manual entry

1. Open the frontend.
2. Enter the course name, issuer, and completion date.
3. Add student names and email addresses.
4. Review the recipient details.
5. Submit the request to generate certificates.

### Option B: Upload a student-list PDF

1. Select the PDF upload option.
2. Upload a text-based PDF containing student names and email addresses.
3. Review the extracted student records.
4. Correct invalid entries and remove unwanted or duplicate records.
5. Confirm the recipient list.
6. Submit the generation job.

The PDF import feature is intended for structured, text-based student lists. Scanned or image-only PDFs may not be supported without OCR. The application should display an error if the document cannot be parsed.

### API request example

A bulk request can also be submitted directly through Swagger UI or an HTTP client.

Send a `POST` request to:

```text
http://127.0.0.1:8000/jobs
```

Example JSON body:

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

A successful request returns HTTP `202 Accepted` with a job ID and its initial status.

Invalid requests return HTTP `422 Unprocessable Entity`.

## 6. Retrieve Job Status and Progress

Use the job ID returned by the creation endpoint.

Send a `GET` request to:

```text
GET /jobs/{job_id}
```

Example:

```text
http://127.0.0.1:8000/jobs/1
```

The response includes job status, course details, recipient totals, successful and failed counts, processed count, progress percentage, and individual recipient outcomes.

Possible final job statuses include:

- `completed`: All recipients succeeded.
- `partially_failed`: Some recipients succeeded while others failed.
- `failed`: No recipients succeeded.

The frontend polls the status endpoint while processing is in progress and displays the latest results.

## 7. Retrieve Generated Certificates

Each successful recipient has a certificate download URL in the job status response.

Use:

```text
GET /jobs/{job_id}/recipients/{recipient_id}/certificate
```

Example:

```text
http://127.0.0.1:8000/jobs/1/recipients/1/certificate
```

A successful request returns a PDF file with the `application/pdf` media type.

The endpoint checks that the recipient belongs to the requested job and that the certificate file is available. Missing jobs, mismatched job-recipient IDs, and unavailable certificates return HTTP `404 Not Found`.

## 8. PDF Student Import

The PDF import endpoint is:

```text
POST /import-students-pdf
```

It accepts a PDF upload using multipart form data and returns extracted student records and validation information for preview.

The import operation does not itself create a certificate-generation job. The user reviews and confirms the imported records before submitting them through the existing job-generation workflow.

The intended student-list format is a table with columns similar to:

| Student Name | Email Address |
|---|---|
| Asif Ali | asif@example.com |
| Rahul Kumar | rahul@example.com |

The parser may recognize equivalent column headings, depending on the implemented extraction rules. The upload endpoint should reject invalid files and handle documents with missing or malformed student information.

Scanned PDFs require OCR, which is outside the basic text-extraction workflow unless separately implemented.

## 9. Run Automated Tests

From the project root, activate the backend virtual environment and run:

```powershell
python -m pytest -v
```

The backend test suite covers health checks, request validation, job creation, progress tracking, PDF downloads, individual-recipient failure isolation, and 404 handling.

The PDF import functionality should also be tested for valid uploads, invalid files, malformed records, duplicate emails, and file-size limits.

Run the frontend production build:

```powershell
cd frontend
npm run build
```

Run any configured frontend lint or test commands from the frontend directory.

## 10. Data Storage

The application stores data locally.

**SQLite database:** `certificate_generator.db`

Stores generation jobs, course details, recipient names and email addresses, processing statuses, success/failure counts, file paths, and error messages.

**Generated PDF files:** `generated_certificates/`

Stores individual PDF certificates created by the application. The database stores the paths to these files rather than their binary contents.

Uploaded student-list PDFs are processed for extraction and should not be retained permanently unless the implementation explicitly requires it.

The database and generated PDFs remain on the backend computer until they are deleted. Removing the database does not automatically delete generated PDFs, and removing PDFs does not automatically remove database records.

## 11. Important Design Decisions

### Relational database

SQLite and SQLAlchemy are used to persist job and recipient information. Jobs and recipient outcomes are stored separately, with each recipient linked to its parent job through a foreign key.

This supports per-recipient status tracking and job-level progress calculation.

### Shared generation workflow

Manual entry and PDF import both produce the same recipient data structure and use the existing job-generation endpoint. This avoids maintaining separate certificate-generation implementations.

### Input validation

Pydantic validates API requests on the backend. Frontend validation improves usability, but the server remains authoritative.

PDF-imported records are previewed and corrected before job submission.

### Individual failure isolation

Each recipient is processed independently. If generating one certificate fails, the application records the error and continues processing the remaining recipients.

### Local file storage

ReportLab generates individual PDF files in the local output directory. This is simple for a development assignment but requires additional storage management for a larger production deployment.

### Background processing

FastAPI `BackgroundTasks` is used to process generation jobs after the API accepts the request. It is suitable for this simple application but is not a durable job queue. If the process stops unexpectedly, unfinished jobs are not guaranteed to resume automatically.

A production system could use a durable task queue and worker processes.

### Theme support

The frontend supports dark and light themes to improve usability in different environments.

## 12. Limitations

- The application uses local SQLite and filesystem storage.
- The current background-task approach does not guarantee recovery of interrupted jobs.
- PDF import depends on the layout and text extractability of the uploaded document.
- Scanned PDFs require OCR if image-based student lists must be supported.
- The application is intended as a development and assignment project rather than a production-hardened multi-user service.

## License

Add an appropriate license if you intend to distribute or reuse this project publicly.