# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the container's port available to the outside world (optional, remove if unnecessary)
EXPOSE 8080

# Define environment variable for OpenAI API key (you can pass this at runtime for security)
ENV OPENAI_API_KEY=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

# Run the script when the container launches
CMD ["python", "openai_integration.py"]
