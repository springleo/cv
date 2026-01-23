# Use Python as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Flask dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose the PORT (Cloud Run will use 8080 by default)
EXPOSE 8080

# Set environment variable for Flask
ENV FLASK_APP=app.py

# Run Flask app, listening on the PORT environment variable
CMD ["python", "-u", "app.py"]
