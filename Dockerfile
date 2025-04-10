# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    exiftool \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#libheif-dev \
#libjpeg-dev \

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if needed, e.g., for a web server)
# EXPOSE 5000

# Define environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the script
CMD ["python", "tagger.py"]