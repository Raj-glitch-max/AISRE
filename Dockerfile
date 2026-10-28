# Render deployment Dockerfile for AISRE backend
# Build context: repository root (.)
# This duplicates backend/Dockerfile with paths adjusted for root context

FROM python:3.12-slim

WORKDIR /app

# git is a runtime dependency: get_recent_commits shells out to it
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ /app/

# Copy victim-app source for commit-history tool
COPY victim-app/ /victim-app/

# Copy .git for commit-history tool
COPY .git/ /.git/

ENV PLATFORM=docker \
    PYTHONUNBUFFERED=1

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]