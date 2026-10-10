
# Bulk Certificate Generator

A Python backend API for generating individual PDF certificates
for multiple recipients in a single request.

## Technology Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- ReportLab
- pytest

## Project Status

Initial project setup. API endpoints, database models,
certificate generation, and tests will be implemented incrementally.

## Local Setup

Create and activate a Python virtual environment, then install
the dependencies listed in `requirements.txt`.

## Running the Application

The application entry point will be `app.main:app`.
Run instructions will be finalized after the API is implemented.

## Testing

Run the automated tests using:

```bash
python -m pytest
```

## Design Decisions

The project uses a relational database for job and recipient
records and local filesystem storage for generated PDFs.

Processing strategy, API contracts, validation rules, and
known limitations will be documented after implementation.
  