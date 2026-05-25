FROM python:3.10-slim

WORKDIR /app

# Copy script and configuration
COPY gmail_bulk_trash.py .
COPY senders.json .
COPY README.md .

# Install dependencies
RUN pip install --no-cache-dir \
    google-auth \
    google-auth-oauthlib \
    google-api-python-client

# Non-root user for security
RUN useradd -m -u 1000 gmail && chown -R gmail:gmail /app
USER gmail

# Entrypoint
ENTRYPOINT ["python3", "gmail_bulk_trash.py"]
CMD ["--help"]
