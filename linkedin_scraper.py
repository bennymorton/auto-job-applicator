
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time

# Set up the Chrome driver
# service = Service('path/to/chromedriver')  # Update with the path to your chromedriver
# driver = webdriver.Chrome(service=service)

options = Options()
# options.add_argument("--headless")
# options.add_argument("--no-sandbox")
options.add_argument("enable-automation")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# LinkedIn jobs URL
url = "https://www.linkedin.com/jobs/search/?currentJobId=3768267063&f_E=1%2C2&f_TPR=r2592000&f_WT=3%2C2&geoId=90009496&keywords=%22devops%20engineer%22&location=London%20Area%2C%20United%20Kingdom&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true"
driver.get(url)

# Initialize an empty list to hold job data
jobs = []

# Scroll and extract job data
while True:
    # Wait for the job cards to be visible
    job_cards = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'base-card'))
    )

    # Extract job details
    for job_card in job_cards:
        try:
            job_title = job_card.find_element(By.CSS_SELECTOR, 'h3.base-search-card__title').text.strip()
            company_name = job_card.find_element(By.CSS_SELECTOR, 'h4.base-search-card__subtitle').text.strip()
            location = job_card.find_element(By.CSS_SELECTOR, 'span.job-search-card__location').text.strip()
            posted_date = job_card.find_element(By.CSS_SELECTOR, 'time').get_attribute('datetime')
            job_link = job_card.find_element(By.CSS_SELECTOR, 'a.base-card__full-link').get_attribute('href')

            # Click on the job card to load the full job description and details
            job_card.click()
            time.sleep(3)  # Wait for the job details to load

            # Extract the full job description
            job_description = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'show-more-less-html__markup'))
            ).text.strip()

            # Extract the industry (if available)
            try:
                industry = driver.find_element(By.XPATH, "//li[contains(text(), 'Industry')]/span").text.strip()
            except:
                industry = 'Not specified'

            jobs.append({
                'job_title': job_title,
                'company_name': company_name,
                'location': location,
                'posted_date': posted_date,
                'job_link': job_link,
                'job_description': job_description,
                'industry': industry
            })
        except Exception as e:
            print(f"Error extracting job details: {e}")
            continue

    # Scroll down to load more jobs
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
    
    # Wait to load the new jobs
    time.sleep(3)
    
    # Check if there are no new jobs loaded (end of the list)
    new_job_cards = driver.find_elements(By.CLASS_NAME, 'base-card')
    if len(new_job_cards) == len(job_cards):
        break

print(jobs)
print(len(jobs))

# Clean up and close the browser
driver.quit()
