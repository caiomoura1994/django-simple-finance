# Django Simple Finance

A multi-user personal finance REST API built with Django and Django REST Framework. The project manages accounts, categories, transactions, suppliers, and asynchronous transaction imports from Excel and OFX files.

The main engineering focus is the transaction import pipeline: an uploaded file is registered as an import, queued with Celery, routed to the appropriate processor, validated, and converted into user-owned financial records while its progress is tracked by the API.

## Highlights

- Token-based authentication and user profile management
- Per-user data isolation for financial resources
- Account, category, transaction, and supplier APIs
- Filtering, search, ordering, and financial summaries
- Asynchronous Excel and OFX imports with Celery and Redis
- Extensible processor architecture using Strategy and Factory patterns
- Import status and progress tracking
- OpenAPI schema with Swagger UI and ReDoc
- Structured application logging with Loguru
- Automated API and processor tests with pytest

## Import architecture

```mermaid
flowchart LR
    A[Client uploads file] --> B[Django REST API]
    B --> C[TransactionImport: PENDING]
    C --> D[Redis queue]
    D --> E[Celery worker]
    E --> F[ProcessorFactory]
    F -->|.xlsx / .xls| G[Excel processor]
    F -->|.ofx / .qfx| H[OFX processor]
    G --> I[Validate and map rows]
    H --> I
    I --> J[Categories and accounts]
    J --> K[Transactions]
    K --> L[Update import status and counters]
```

The `TransactionProcessor` interface keeps file-specific parsing separate from task orchestration. `ProcessorFactory` selects an implementation from the uploaded file extension, making additional formats possible without changing the Celery task.

## Technology stack

- Python
- Django 4.2
- Django REST Framework
- Celery 5
- Redis
- SQLite for local development; PostgreSQL-compatible configuration through `DATABASE_URL`
- pandas and openpyxl for Excel processing
- ofxparse for OFX processing
- drf-spectacular for OpenAPI documentation
- pytest and pytest-django
- Loguru and Google Cloud Logging

## Project structure

```text
business_suppliers/              Supplier and supplier-transaction APIs
core/                            Django settings, URLs, Celery and logging
finances/
  accounts/                      Account API
  categories/                    Category API
  transactions/                  Transaction and reporting APIs
  transaction_imports/
    processors/                  Strategy implementations and factory
    tasks.py                     Celery import orchestration
    transaction_import_views.py Upload, processing and template endpoints
identity/                        Registration, authentication and profiles
```

## Local setup

### Prerequisites

- Python 3.9–3.11 with the current dependency set
- Docker with Docker Compose, or a local Redis server

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/caiomoura1994/django-simple-finance.git
cd django-simple-finance

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "numpy<2" -r requirements_dev.txt
```

Apply the database migrations:

```bash
python manage.py migrate
```

Start Redis:

```bash
docker compose up -d redis
```

Configure Celery to reach Redis through the host port:

```bash
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

Start the API:

```bash
python manage.py runserver
```

In another terminal, activate the virtual environment, export the same Celery variables, and start a worker:

```bash
source .venv/bin/activate
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
celery -A core worker --loglevel=info
```

## API documentation

With the development server running:

- Swagger UI: <http://127.0.0.1:8000/api/docs/>
- ReDoc: <http://127.0.0.1:8000/api/redoc/>
- OpenAPI schema: <http://127.0.0.1:8000/api/schema/>

Protected endpoints accept a Django REST Framework token:

```http
Authorization: Token <your-token>
```

The main API groups are:

- `/api/auth/` — registration, login, profile, password change, and logout
- `/api/finances/accounts/` — accounts and balance adjustments
- `/api/finances/categories/` — transaction categories
- `/api/finances/transactions/` — transactions and financial summaries
- `/api/finances/transaction-imports/` — file uploads, processing, and import status
- `/api/suppliers/` — suppliers and related transactions

## Excel import format

An Excel import requires these columns:

| Column | Example | Description |
| --- | --- | --- |
| `date` | `2026-09-20` | Transaction date |
| `description` | `Grocery store` | Human-readable description |
| `amount` | `150.75` | Positive monetary amount |
| `kind_of_transaction` | `EXPENSE` | `INCOME` or `EXPENSE` |
| `category` | `Food` | Category name |
| `account` | `Main Account` | Account name |

A ready-to-use spreadsheet can also be generated through the transaction-import template endpoint exposed in Swagger UI.

## Running the tests

```bash
pytest
```

The suite covers authentication, account and category operations, transaction summaries, ownership validation, Excel/OFX processing, processor selection, file uploads, and asynchronous import dispatch.

To run a focused part of the suite:

```bash
pytest finances/transaction_imports/
```

## Design considerations

- Every primary finance model belongs to a user, and API querysets are scoped to the authenticated owner.
- File parsing is selected through a factory instead of branching inside the task.
- Imports are processed outside the request-response cycle so larger files do not block an API worker.
- Import records expose status, item counts, task IDs, and error information for operational visibility.
- SQLite keeps local setup lightweight, while `DATABASE_URL` allows a production database such as PostgreSQL.

## Production hardening

Before operating the project as a production financial system, the next priorities would be:

- make import dispatch idempotent and prevent duplicate processing;
- claim imports atomically before queueing and enforce valid status transitions;
- use database transactions and batch inserts for all-or-nothing imports;
- preserve OFX transaction identifiers and detect duplicates;
- validate file size, content type, extension, and source consistency;
- normalize imported datetimes into timezone-aware values;
- move uploaded files to durable object storage;
- add retry policies, dead-letter handling, metrics, and alerts;
- configure production security settings and secret management.
