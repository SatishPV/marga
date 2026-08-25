FROM python:3.12-slim

WORKDIR /app

# Install the package first (better layer caching — deps change less
# often than app code)
COPY pyproject.toml README.md LICENSE ./
COPY marga ./marga
COPY sample_data ./sample_data
COPY ui ./ui

RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Runs the API + web UI. Catalog scans/vitals are still available via
# `docker exec <container> marga scan ...` for CLI use inside the container.
CMD ["marga", "serve", "--port", "8000"]
