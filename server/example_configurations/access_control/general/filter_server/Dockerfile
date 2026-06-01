FROM python:3.12-slim

RUN pip install --no-cache-dir flask requests

WORKDIR /app
COPY app.py .

ENV UPSTREAM_REPOSITORY_URL="http://repository:80"
ENV POLICY_DATA_PATH="/policies/data.json"
ENV PORT="8080"

EXPOSE 8080

CMD ["python", "app.py"]
