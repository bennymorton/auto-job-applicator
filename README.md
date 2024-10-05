# Automatic AI Job Collector, Analyser and Applicator

## Commit Log
**21/08/24: Initial commit**
Including basic LinkedIn scraper code, to scroll job board and collate results.

**05/10/24: PoC complete**
- Web scraping from local machine fully successful
- Uploads scraped data to RDS instance
- Second script:
    - Pulls new rows from RDS instance and runs them through the OpenAI API to gather deeper insights about each job
    - Then uploads these insights plus basic job details to personal Notion database for easy and simple viewing
