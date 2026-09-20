FROM python:3.12-slim

WORKDIR /app

# git is a runtime dependency, not a build one: get_recent_commits shells out to it as
# an investigation tool, so the image needs both the binary and the repo history.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
# victim-app's source travels with the image so the commit-history tool has a repo to
# read. The .git directory is supplied by the build context.
COPY victim-app/ /victim-app/
COPY .git/ /.git/

ENV PLATFORM=ecs \
    PYTHONUNBUFFERED=1

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
