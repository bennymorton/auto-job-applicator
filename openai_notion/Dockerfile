# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY /openai_notion/* /app

COPY ../db_utils.py /app

COPY ../creds.yaml /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the container's port available to the outside world (optional, remove if unnecessary)
EXPOSE 8080

# Run the script when the container launches
# CMD ["python", "openai_integration.py"]
