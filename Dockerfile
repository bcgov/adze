FROM python:3.9

WORKDIR /app

# Copy dependencies and script
COPY requirements.txt .
COPY run_script.sh .

# Copy the rest of the code
COPY . .

# Make sure the run script is executable
RUN chmod +x /app/run_script.sh

# Set default environment variables
ENV INPUT_DIR=/app/data/input \
  OUTPUT_DIR=/app/data/output \
  REPORT_DIR=/app/data/report

# Ensure folders exist
RUN mkdir -p $INPUT_DIR $OUTPUT_DIR $REPORT_DIR

# Entry point to run the CLI
CMD ["./run_script.sh"]
