#!/bin/bash

# Run the scraper and log the output
python3 linkedin_scraper_local.py >> logs/scraper_logfile.log 2>&1

# Sleep for 1 hour
sleep 3600

# Run the ingestion script and log the output
python3 /openai_notion/openai_notion_integration.py >> logs/openai_notion_logfile.log 2>&1
