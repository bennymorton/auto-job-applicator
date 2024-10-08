# Automatic AI Job Collector, Analyser and Applicator
## About The Project
This is the problem: the job hunting process in tech today is extremely tedious and convoluted. It involves scrolling through multiple different job boards, repeatedly searching for your specific needs and sifting through piles of rubbish. 
Some of the job descriptions are literally thousands of lines long, others are total vapour; as in the company isnt even hiring at all.

***It's about time someone automated this process.***

This project is designed to scrape jobs from LinkedIn of a pre-defined title and filter selection, then load that data into an AWS RDS database. 
Separately, a script then feeds that data from the database through the OpenAI API to gather deeper insights and summarise the hefty job descriptions. This data is then sent via the Notion API to a Notion database, to utilise Notion's customisability.

## Update Log
### V0.0.2
better job filters

### V0.0.1
Cronjob which runs every night and scrapes new jobs, followed by second cron job which pulls new jobs from db and loads into notion
- cookies 

### V0.0.0
**Collect relevant jobs, then collate and display them in a format where i can give a no/no-go for each, with minimal friction**
- ’interest’ figure calculated and displayed, informed by:
  - progressive workplace (hybrid/remote/flexible working hours)
  - aligned stack
  - preferred industry

## Roadmap
**V0.1:**
- **V0.1.0:** Containerised scripts which run from EC2 instance, meaning entire setup is fully contained in the cloud
- **V0.2.0:** pagination
- **V0.3.0:** tested and fine-tuned interest calculation. separate signal from noise

### V1
- apply to each job with a custom CV and optional cover letter tailored to the tools, processes and skills required for the job
- send outreach messages to relevant linkedin recruiters/HMs

### V2
- *scale.*
- modify scraper to get all jobs, not personally filtered
- modify openai-notion integration to pull only relevant ones to a set of personal filters 

## To-Dos
### General
- [ ] Full unit testing
- [ ] Implement some more sophisticated logging. Instead of just print statements.

### Scraper
- [ ] figure out how to get posted_date for jobs after they have been changed to 'Viewed' (the time tag seems to disappear)
    `posted_date = driver.find_element(By.CSS_SELECTOR, 'time').get_attribute('datetime')`
- [ ] build pagination function, then loop `scrape_page()`
- [ ] finish ordering results by "Most Recent" (struggling to select "show results" button)
```
    all_filters = driver.find_element(By.XPATH, "//button[text()='All filters']")
    all_filters.click()
    most_recent = driver.find_element(By.XPATH, "//span[text()='Most recent']")
    most_recent.click()
    time.sleep(10)
    show_results = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'results')]"))
            )
    show_results.click()
```