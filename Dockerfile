# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory
COPY . .

# Expose the port that the Flask app will run on
EXPOSE 5000

# Set environment variables (if needed)
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Run the app with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]