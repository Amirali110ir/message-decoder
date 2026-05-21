FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Configure Liara's official PIP mirror
ENV PIP_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple
# Install Python dependencies
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI backend code
COPY apps/api/app ./app

# Copy the pre-built Next.js static output from the local machine
# This bypasses the slow Node.js compilation on the cloud server
COPY apps/web/out ./web_static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
