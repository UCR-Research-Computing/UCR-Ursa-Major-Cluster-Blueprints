# UCR Research Computing Dashboard API

## Overview

This project provides a Flask-based API for managing entities related to university research computing, including researchers, labs, projects, compute resources, and grants. It also integrates with Google's Gemini API for AI-powered features like text summarization, notes analysis, and search.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python**: Version 3.9+
*   **Pip**: Python package installer (usually comes with Python)
*   **PostgreSQL**: A running PostgreSQL server. This is needed for storing application data.
    *   For local development, you can install PostgreSQL directly on your machine.
    *   For cloud deployment (e.g., Google Cloud Platform), a managed instance like Cloud SQL is recommended.
*   **Google Gemini API Key**: Access to the Google Gemini API and a valid API Key.

## Setup Instructions

Follow these steps to get your development environment set up:

1.  **Clone the Repository**:
    ```bash
    git clone <your-repository-url>
    cd <repository-name>
    ```

2.  **Create and Activate a Python Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
    This keeps your project dependencies isolated.

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a file named `.env` in the root of the project. This file will store your local configuration settings. **Do not commit this file to version control if it contains sensitive credentials.**

    Populate the `.env` file with the following, replacing placeholder values with your actual settings:
    ```env
    FLASK_APP=app.py
    FLASK_ENV=development # Use 'production' for production environments
    # FLASK_DEBUG=1 # Optional: enables debug mode, useful for development

    # Replace with your actual PostgreSQL connection string
    # Format: postgresql+psycopg2://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
    DATABASE_URL=postgresql+psycopg2://your_db_user:your_db_password@localhost:5432/ucr_research_db

    # Replace with your actual Google Gemini API Key
    API_KEY=YOUR_GEMINI_API_KEY_HERE
    ```

5.  **Database Setup**:
    *   **Create PostgreSQL Database**:
        *   Ensure your PostgreSQL server is running.
        *   Connect to PostgreSQL (e.g., using `psql`).
        *   Create a new database (e.g., `ucr_research_db`):
            ```sql
            CREATE DATABASE ucr_research_db;
            ```
        *   Create a new user and grant privileges (replace `your_db_user` and `your_db_password`):
            ```sql
            CREATE USER your_db_user WITH PASSWORD 'your_db_password';
            GRANT ALL PRIVILEGES ON DATABASE ucr_research_db TO your_db_user;
            ALTER ROLE your_db_user CREATEDB; -- Optional, useful if user needs to create DBs for tests
            ```
            *Note: For production, grant only necessary privileges.*
    *   **Run Database Migrations**:
        This command initializes your database schema based on the defined models.
        ```bash
        flask db upgrade
        ```
        If you are setting up for the first time and the `migrations` folder does not exist or is empty (e.g., after a fresh clone before any migrations are generated):
        ```bash
        # (If migrations folder doesn't exist or is empty after a fresh clone)
        # flask db init  # Run this only once if 'migrations' folder is missing
        # flask db migrate -m "Initial database schema" # Create the first migration if needed
        flask db upgrade # Then upgrade
        ```
        Typically, after cloning a project with existing migrations, only `flask db upgrade` is needed.

## Running the Development Server

1.  **Start the Flask Application**:
    ```bash
    flask run
    ```
2.  The application will typically start on `http://127.0.0.1:5000/`.
3.  **Accessing the API**:
    API endpoints are available under the `/api` prefix, e.g., `http://127.0.0.1:5000/api/researchers`.
4.  **Accessing API Documentation (Swagger UI)**:
    Navigate to `http://127.0.0.1:5000/api/docs` in your browser.

## Running with Gunicorn (Production-like Environment)

For a more production-like setup locally, or for deployment, you can use Gunicorn:

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```
This will start Gunicorn on port 8000, accessible from other devices on your network if firewall rules permit.

## API Endpoints Overview

The API provides endpoints for managing various research computing entities:

*   **Researchers**: Manage researcher profiles and their notes.
*   **Labs**: Manage research labs, their PIs, members, and associated projects.
*   **Projects**: Manage research projects, including linking to PIs, labs, compute resources, and grants.
*   **Compute Resources**: Manage computational resources and their allocation to projects.
*   **Grants**: Manage grant information, including PIs, Co-PIs, and associated projects.
*   **AI Services**:
    *   Text summarization.
    *   Analysis of researcher notes (sentiment, key themes, summary).
    *   Global search across all data entities.
    *   External grant search based on criteria.
    *   Drafting grant introduction emails.
*   **Data Import/Export**: Endpoints for bulk import and export of application data.

For detailed information on all endpoints, request/response formats, and schemas, please refer to the **API Documentation** available at `/api/docs` when the application is running.

## (Optional) Google Cloud Platform (GCP) Deployment Notes

Deploying this application to Google Cloud Platform (e.g., using Cloud Run and Cloud SQL) involves these general steps:

*   **Containerization**: Create a `Dockerfile` to package the application. (A `Dockerfile` will be provided in a later step if specified for the project).
*   **Cloud SQL**:
    *   Set up a PostgreSQL instance on Cloud SQL.
    *   Configure the `DATABASE_URL` environment variable in your Cloud Run service to connect to this instance (often using the Cloud SQL Proxy connection string format).
*   **Environment Variables**: Set `FLASK_ENV=production`, `DATABASE_URL`, and `API_KEY` in the Cloud Run service configuration.
*   **Database Migrations on GCP**: Migrations (`flask db upgrade`) need to be run against the Cloud SQL database. This can be done:
    *   By connecting to the database via the Cloud SQL Proxy from a local machine or a VM and running the command.
    *   As a one-off job or script during deployment.
    *   (Less common for Flask-Migrate) As part of the application startup sequence if designed to do so (requires careful implementation).
*   **Cloud Run**: Deploy the container image to Cloud Run, configuring environment variables and Cloud SQL connections.

Refer to Google Cloud documentation for detailed instructions on deploying Python applications with Cloud Run and Cloud SQL.
