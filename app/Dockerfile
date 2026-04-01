FROM python:slim

# Set environment variables for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m compileall -f . \
    && chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
