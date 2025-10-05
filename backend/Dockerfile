# Flask API only
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


COPY requirement.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip install gunicorn

# copy backend code
COPY . /app

EXPOSE 5000
# gunicorn serves Flask app: app:app (from backend/app.py -> app = create_app())
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
