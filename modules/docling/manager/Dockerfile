FROM python:3.13.18-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Status polling is frequent, so the access log is off; the app logs jobs and worker changes.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001", "--no-access-log"]
