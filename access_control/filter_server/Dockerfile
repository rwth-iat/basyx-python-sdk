# Response filter of the access control layer. Build from this directory:
#   docker build -t basyx-access-filter access_control/filter_server
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY access_filter ./access_filter

USER nobody
EXPOSE 8080

# Settings come from the environment, see access_filter/config.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "access_filter.app:create_app()"]
