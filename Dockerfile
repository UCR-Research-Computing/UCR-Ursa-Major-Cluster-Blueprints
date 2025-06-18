# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
# FLASK_APP is set in .flaskenv, but good to have defaults if .flaskenv isn't copied or used in prod
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Let Flask know it's behind a proxy and to trust X-Forwarded-Proto
ENV FLASK_RUN_HOST=0.0.0.0
# Note: FLASK_ENV=production or similar should be set via Cloud Run env vars, not fixed here.
# DATABASE_URL and API_KEY will be set as environment variables in the Cloud Run service.

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any, e.g., for psycopg2 if not using -binary)
# For psycopg2-binary, typically no extra system deps are needed.
# RUN apt-get update && apt-get install -y some-package

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port Gunicorn will run on (Cloud Run expects 8080 by default)
EXPOSE 8080

# Define the command to run the application using Gunicorn
# The number of workers can be tuned. (2 * $num_cores) + 1 is a common starting point.
# Ensure 'app:app' correctly points to your Flask app instance (e.g., in app.py, the Flask instance is named 'app').
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
