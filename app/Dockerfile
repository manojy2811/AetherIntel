FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements or setup direct pip install
# Since we have specific dependencies:
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    pydantic-settings \
    langchain \
    langchain-google-genai \
    langgraph \
    sqlalchemy \
    psycopg2-binary \
    httpx \
    beautifulsoup4

# Copy source code
COPY . /workspace/app

EXPOSE 8000

ENV PYTHONPATH=/workspace

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
