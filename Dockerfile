FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency definition
COPY pyproject.toml ./

# Install dependencies into system environment for Docker
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY parse_result.json /app/
COPY app /app/app/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
