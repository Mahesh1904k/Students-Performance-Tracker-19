# Use official Python 3.12 image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Copy all project files
COPY . .

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port (used by gunicorn)
EXPOSE 10000

# Start your Flask app using gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
