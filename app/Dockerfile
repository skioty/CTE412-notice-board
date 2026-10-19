# Purpose: Build all three Notice Board releases from one source tree.
# Build from the repository root using the commands in Task 2.

FROM python:3.12-alpine

# Build arguments identify the release and student.
ARG APP_VERSION=1.0.0
ARG STUDENT_ID=02230141

# Preserve the build values for the running application.
ENV APP_VERSION=${APP_VERSION} \
    STUDENT_ID=${STUDENT_ID} \
    FEATURE_PINNED=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Use an unprivileged account with a stable numeric identity.
RUN addgroup -S -g 10001 appgroup \
    && adduser -S -D -H -u 10001 -G appgroup appuser

COPY --chown=appuser:appgroup server.py /app/server.py

USER 10001:10001

EXPOSE 8080

CMD ["python", "/app/server.py"]