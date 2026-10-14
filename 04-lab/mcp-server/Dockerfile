# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency files. The app is a script (weather.py), not an installable package.
COPY pyproject.toml uv.lock ./

# Install locked dependencies into the image Python, without installing this repo as a package.
RUN pip install --no-cache-dir uv \
    && uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy application code
COPY weather.py ./

# Expose port (Cloud Run will override this)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "weather.py"]
