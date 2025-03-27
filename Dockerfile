# Use official Python 3.9 base image
FROM python:3.9

# Install system dependencies for venv
RUN apt-get update && apt-get install -y python3-venv

# Set the working directory inside the container
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else into the container
COPY . .

# Ensure your run script and entrypoint are executable
RUN chmod +x /app/run_script.sh /app/entrypoint.sh

# Set default environment variables for input/output/report folders
ENV INPUT_DIR=/app/data/input \
  OUTPUT_DIR=/app/data/output \
  REPORT_DIR=/app/data/report \
  MODE=web \
  FLASK_APP=webserver.py


# Create the folders if they don't exist
RUN mkdir -p $INPUT_DIR $OUTPUT_DIR $REPORT_DIR

# Use entrypoint script to switch between web and CLI mode
CMD ["./entrypoint.sh"]
