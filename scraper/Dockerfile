# Stage 1: Build with cross-compilation support
FROM --platform=$BUILDPLATFORM tonistiigi/xx AS xx

# Main image
FROM --platform=$BUILDPLATFORM python:3.12-slim

# Install xx scripts
COPY --from=xx / /

# Use xx-apt-get for target-aware package installation
ARG TARGETPLATFORM
# Install firefox
RUN xx-apt-get update && \
    xx-apt install firefox-esr -y && \
    rm -rf /var/lib/apt/lists/* 

# Python and local env setup
WORKDIR /app

COPY /scraper/* /app

COPY ../db_utils.py /app

RUN pip install --upgrade pip

RUN pip install -r requirements.txt    

CMD ["python", "linkedin_scraper.py"]       
