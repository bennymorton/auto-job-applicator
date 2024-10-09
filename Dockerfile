FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

COPY linkedin_scraper.py /app/
COPY openai_notion_integration.py /app/
COPY db_utils.py /app/
COPY requirements.txt /app/
COPY cookies.pkl /app/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Firefox and cron
RUN apt-get update && \
    apt install firefox-esr -y && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/* 

# Add crontab file to the cron.d directory
COPY cronjob /etc/cron.d/scheduler

# Give execution rights on the cron job file
RUN chmod 0644 /etc/cron.d/scheduler

# Apply the cron job
RUN crontab /etc/cron.d/scheduler

# Ensure the credentials file will be mounted later and handle permissions
RUN mkdir /app/creds

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

EXPOSE 8080

# Start cron and keep the container running, outputting logs
CMD cron && tail -f /var/log/cron.log




