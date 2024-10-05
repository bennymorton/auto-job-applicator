import pickle
import re
import subprocess
import time
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from db_utils import Database_connector


def get_driver():
    firefox_driver_install = GeckoDriverManager().install()

    # Print the version of the driver
    try:
        # Use subprocess to get the ChromeDriver version
        version_output = subprocess.check_output([firefox_driver_install, "--version"], stderr=subprocess.STDOUT).decode('utf-8')
        print(f"Installed FirefoxDriver version: {version_output}")
        print("############################")
    except Exception as e:
        print(f"Error fetching FirefoxDriver version: {e}")

    options = Options()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-dev-shm-usage') 
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")

    driver = webdriver.Firefox(
        service=FirefoxService(firefox_driver_install), 
        options=options
        )

    return driver

def catch_page_redirect(driver, url):
    print("Checking we're on the correct page...")
    # TODO: change this while True so it doesnt potentially drain resources
    while True:
        # Check if the current URL is correct (and that the page hasnt redirected)
        if driver.current_url == url:
            print('We are!')
            break
        else:
            print('Page redirect has occurred. Restarting driver.')
            driver.quit()
            time.sleep(5)  
            driver = get_driver()
            time.sleep(10) 
            driver.get(url)
            time.sleep(10)  

def scrape_job(driver, job_card, database_connector):
    job_title_raw = job_card.find_element(By.CSS_SELECTOR, 'a.job-card-list__title').text.strip()

    # Use regular expressions to capture the repeating part
    match = re.match(r"(.+?)\s*\1.*", job_title_raw)
    if match:
        job_title = match.group(1).strip()
    else:
        job_title = job_title_raw.strip()

    company_name = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.job-details-jobs-unified-top-card__company-name > a:nth-child(1)'))
        ).text.strip()
    job_id = (job_title + company_name).replace(" ", "_")

    # Check if job already exists in DB (read)
    sql_string = f"SELECT * FROM bens_jobs WHERE job_id = '{job_id}'"
    sql_output = database_connector.query_db(sql_string)
    row = sql_output.fetchone()
    if row is None:
        print('Found new job: ', job_id)
        pass
    else:
        return None
    
    job_link = job_card.find_element(By.CSS_SELECTOR, 'a.job-card-list__title').get_attribute('href')
    location_wrapper = driver.find_element(By.CSS_SELECTOR, '.job-details-jobs-unified-top-card__primary-description-container')
    location = location_wrapper.find_element(By.CLASS_NAME, 'tvm__text').text.strip()
    job_description = driver.find_element(By.CSS_SELECTOR, 'div.jobs-description__content').text.strip()
    # TODO: figure out how to get posted_date for jobs after they have been changed to 'Viewed' (the time tag seems to disappear)
    # posted_date = driver.find_element(By.CSS_SELECTOR, 'time').get_attribute('datetime')
    
    job_dict = {
        'job_id': job_id,
        'job_title': job_title,
        'company_name': company_name,
        'location': location,
        # 'posted_date': posted_date,
        'job_link': job_link,
        'job_description': job_description,
        'in_notion': False
    }

    return job_dict
   
def scrape_page(driver, database_connector):
    # Initialize an empty list to hold job data
    jobs = []
    time.sleep(20)
    job_cards = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'jobs-search-results__list-item'))
    )
    print('Found ' + str(len(job_cards)) + ' jobs total. Extracting info now.')

    # Extract job details
    for index, job_card in enumerate(job_cards):
        try:
            job_card.click()  # Click on the job card to load the full job description and details
            time.sleep(10)  # Wait for the job details to load
            job_dict = scrape_job(driver, job_card, database_connector)

            if not job_dict:
                continue
            else:
                jobs.append(job_dict)

            print(str(index + 1) + '. Scraped new job: ' + job_dict['job_title'] + ' at ' + job_dict['company_name'])

        except Exception as e:
            print(f"Error extracting job details: {e}")
            continue

    print('Scraped ' + str(len(jobs)) + ' new jobs.')
    return jobs

def load_cookies(driver):
    # TODO: finish figuring out how to implement cookies successfully
    print('Attempting to load cookies to bypass full sign in')
    cookies = pickle.load(open("/Users/benmorton/Desktop/project_files/auto_job_applicator/scraper/cookies.pkl", "rb"))

    for cookie in cookies:
        try:
            cookie['sameSite'] = "None; Secure" # Apply cookies to cross-site requests as well
            driver.add_cookie(cookie)
            print('Cookie added')
        except Exception as e:
            print('Failed to load cookie. Error: ', e)
            continue
    
def login_to_linkedin(driver, email, password):
    # Check for 'Sign in with Google' blocking modal
    try:
        print('Looking for the Google sign in modal')
        google_modal_iframe = driver.find_element(By.CSS_SELECTOR, "iframe")
        driver.switch_to.frame(google_modal_iframe) # Switch to iframe containing the Google sign in modal
        google_modal_close_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, 'close'))
        )
        google_modal_close_button.click()
        print('Closing Google Sign in modal')
        time.sleep(10)

    except:
        print('No Google Sign in modal')
        pass

    driver.switch_to.default_content() # Switch back to the default context (not the iframe)
    sign_in_button = driver.find_element(By.LINK_TEXT, "Sign in")
    sign_in_button.click()
    time.sleep(5) 

    email_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")    
    email_field.send_keys(email)
    password_field.send_keys(password)

    sign_in_submit = driver.find_element(By.XPATH, "//button[@type='submit']")
    sign_in_submit.click()

    time.sleep(10)

    if "challenge" in driver.current_url:
        print("Verification Captcha occurred. Needs human intervention.")
        print(driver.current_url)
        return None
    else:
        print('Successfully signed in!')
        # Get cookies and save into a pickle file
        cookies = driver.get_cookies()
        with open('cookies.pkl', 'wb') as file:
            pickle.dump(cookies, file)

def search_jobs(driver, preferred_job_title):
    print('Navigating to jobs page')
    jobs_button = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "li.global-nav__primary-item:nth-child(3) > a:nth-child(1)"))
    )
    jobs_button.click()
    time.sleep(10) 

    jobs_search_input_box = driver.find_element(By.XPATH, "/html/body/div[7]/header/div/div/div/div[2]/div[2]/div/div/label/following-sibling::input[1]")
    jobs_search_input_box.click()
    time.sleep(5)
    jobs_search_input_box.send_keys(preferred_job_title)
    jobs_search_input_box.send_keys(Keys.ENTER)

def set_job_filters(driver, job_filters):
    experience_level = driver.find_element(By.ID, 'searchFilter_experience')
    experience_level.click()
    time.sleep(5)
    # workplace_type = driver.find_element(By.ID, 'searchFilter_workplaceType')

def master_scraper(url, email, password, preferred_job_title, job_filters, database_connector):
    driver = get_driver()
    time.sleep(5) 

    driver.get(url)

    catch_page_redirect(driver, url)
    time.sleep(10) 
    
    # TODO: figure out cookies
    # try:
    #     load_cookies(driver, password)
    # except Exception as e:
    #     print('Failed to load cookies. Error: ')
    #     print(e)
    #     login_to_linkedin(driver, email, password)
    #     time.sleep(5) 

    result = login_to_linkedin(driver, email, password)
    if result is None: # If verification captcha has popped up
        return
    
    search_jobs(driver, preferred_job_title)
    time.sleep(5)

    # TODO: Add filters 
    # set_job_filters(driver, job_filters)
    # time.sleep(5)

    jobs = scrape_page(driver, database_connector)
    # TODO: build pagination function, repeat `scrape_page`

    driver.quit()

    return jobs
    
linkedin_url = "https://www.linkedin.com/"

preferred_job_title = 'DevOps Engineer'
job_filters = {'experience_level': ['Entry Level']}

if __name__ == "__main__":
    database_connector = Database_connector()
    # Load credentials from creds.yaml
    with open('creds.yaml', 'r') as file:
        creds = yaml.safe_load(file)
    
    email = creds['LINKEDIN_EMAIL']
    password = creds['LINKEDIN_PASSWORD']
    
    jobs = master_scraper(
        linkedin_url, 
        email, 
        password, 
        preferred_job_title,
        job_filters,
        database_connector
        )

    # dev_jobs = [
    #     {
    #         'job_id': "4",
    #         'job_title': "test",
    #         'company_name': "test",
    #         'location': "test",
    #         'job_link': "test",
    #         'job_description': "Excellent opportunity for AWS DevOps Engineer to be part of our Cloud Infrastructure & Security services practice. Cognizant Infrastructure Services – Provides IT infrastructure & Cloud services for clients across industry verticals, including both Consulting/Professional and Managed Services, across Enterprise Computing, Cloud services, Security Services, DevOps, Data Centres, End User Computing, Service Desk, Network Services and Environment Management Services.\nCandidate should be eligible for SC clearance or SC cleared\n\nKey Responsibilities\n\n    Developing automation in Terraform for provisioning AWS cloud resources\n    Scripting silent installation of MSI packages\n    Provisioning AWS resources using Terraform pipeline\n    Installation of Bluecrest components, admin server, web server, Output manager and configuration on windows ec2\n    Automation of bluecrest components installation using PowerShell\n    To Manage and re-factor housekeeping scripts written in powershell, python.\n    Responsible to setup FTP service on windows server\n    Assisting other team members on common DevOps tasks\n\nKey Skills And Experience\n\n    Should have experience in AWS services EC2, S3, ECS, EKS\n    Should have experience in automation ,Terraform\n    Good experience in scripting using Powershell, Python\n    Experience in Jenkins, Ansible and similar tools\n    Good Stakeholder management skills\n\nAt Cognizant you will experience an exciting mix of innovation by design, creativity, collaboration, and efficiency within a framework of stimulating objectives and a passion for delivering the best to our customers.\n\nYou will be joining a network of some of the most creative, innovative, and dedicated people in the industry with ample opportunities to learn and develop your career.",
    #         'in_notion': "FALSE"
    #     },
    #     {
    #         'job_id': "5",
    #         'job_title': "2",
    #         'company_name': "2",
    #         'location': "2",
    #         'job_link': "2",
    #         'job_description': "Excellent opportunity for AWS DevOps Engineer to be part of our Cloud Infrastructure & Security services practice. Cognizant Infrastructure Services – Provides IT infrastructure & Cloud services for clients across industry verticals, including both Consulting/Professional and Managed Services, across Enterprise Computing, Cloud services, Security Services, DevOps, Data Centres, End User Computing, Service Desk, Network Services and Environment Management Services.\nCandidate should be eligible for SC clearance or SC cleared\n\nKey Responsibilities\n\n    Developing automation in Terraform for provisioning AWS cloud resources\n    Scripting silent installation of MSI packages\n    Provisioning AWS resources using Terraform pipeline\n    Installation of Bluecrest components, admin server, web server, Output manager and configuration on windows ec2\n    Automation of bluecrest components installation using PowerShell\n    To Manage and re-factor housekeeping scripts written in powershell, python.\n    Responsible to setup FTP service on windows server\n    Assisting other team members on common DevOps tasks\n\nKey Skills And Experience\n\n    Should have experience in AWS services EC2, S3, ECS, EKS\n    Should have experience in automation ,Terraform\n    Good experience in scripting using Powershell, Python\n    Experience in Jenkins, Ansible and similar tools\n    Good Stakeholder management skills\n\nAt Cognizant you will experience an exciting mix of innovation by design, creativity, collaboration, and efficiency within a framework of stimulating objectives and a passion for delivering the best to our customers.\n\nYou will be joining a network of some of the most creative, innovative, and dedicated people in the industry with ample opportunities to learn and develop your career.",
    #         'in_notion': "FALSE"
    #     }
    # ]

    print(database_connector.upload_to_db(jobs))
