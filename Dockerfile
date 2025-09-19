# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set environment variables (override in docker-compose or at runtime)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "main.py"]
