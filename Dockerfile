# Use official Python 3.9 base image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else into the container
COPY . .
COPY run_script.sh .

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
