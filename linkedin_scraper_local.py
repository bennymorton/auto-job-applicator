import pickle
import re
import subprocess
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.firefox import GeckoDriverManager
from auto_job_applicator.db_utils import Database_connector


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
    # options.add_argument('--headless') 
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
    print('Attempting to load cookies to bypass full sign in')
    cookies = pickle.load(open("/Users/benmorton/Desktop/project_files/auto_job_applicator/cookies.pkl", "rb"))

    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print('Failed to load cookie. Error: ', e)
            return False
    
    print('Cookies loaded')
    return True
    
def login_to_linkedin(driver, email, password, cookies_loaded):
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
        driver.switch_to.default_content() # Switch back to the default context (not the iframe)
    except:
        print('Could not find Google Sign in modal')

    sign_in_button = driver.find_element(By.LINK_TEXT, "Sign in")
    sign_in_button.click()
    time.sleep(5) 

    # If cookies have been loaded successfully we should be on a different log in page, which doesnt require entering a username
    if (cookies_loaded is True) and ("login" in driver.current_url):
        pass
    else:
        email_field = driver.find_element(By.ID, "username")
        email_field.send_keys(email)

    password_field = driver.find_element(By.ID, "password")    
    password_field.send_keys(password)
    sign_in_submit = driver.find_element(By.XPATH, "//button[@type='submit']")
    sign_in_submit.click()
    time.sleep(10)

    if "challenge" in driver.current_url:
        print("Verification Captcha occurred. Needs human intervention.")
    else:
        print('Successfully signed in!')

        # Get cookies and save into a pickle file
        cookies = driver.get_cookies()
        with open('/Users/benmorton/Desktop/project_files/auto_job_applicator/cookies.pkl', 'wb') as file:
            pickle.dump(cookies, file)

def search_jobs(driver, preferred_job_title):
    jobs_button = driver.find_element(By.CSS_SELECTOR, "li.global-nav__primary-item:nth-child(3) > a:nth-child(1)")
    print('Navigating to jobs page')
    jobs_button.click()
    jobs_search_input_box = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[7]/header/div/div/div/div[2]/div[2]/div/div/label/following-sibling::input[1]"))
        )
    jobs_search_input_box.click()
    
    time.sleep(5)
    jobs_search_input_box.send_keys(preferred_job_title)
    jobs_search_input_box.send_keys(Keys.ENTER)

def set_job_filters(driver, job_filters):
    print('Setting job filters')
   
    def chosen_filters_loop(filter, filter_mapping, show_result_xpath):
        WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.ID, ('searchFilter_' + filter)))
        ).click()

        time.sleep(10)

        for choice in job_filters[filter]:
            dynamic_xpath = f"//*[@id='{filter_mapping[choice]}']/following-sibling::label[1]"
            try:
                element = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.XPATH, dynamic_xpath))
                        )
                time.sleep(3)
                element.click()
                time.sleep(5)
            except Exception as e:
                print('Could not select filter for', filter, '-', choice)
                print('Attempted XPATH:\n', dynamic_xpath)
                print(repr(e))
                traceback.print_exc()
                pass

        show_result = driver.find_element(By.XPATH, show_result_xpath)
        show_result.click()

    # Map dynamically inputted filters to corresponding CSS IDs
    experience_mapping = {
        'Internship': 'experience-1',
        'Entry level': 'experience-2',
        'Associate': 'experience-3',
        'Mid-Senior level': 'experience-4',
        'Directory': 'experience-5',
        'Executive': 'experience-6'
        }
    experience_show_result_xpath = "/html/body/div[7]/div[3]/div[4]/section/div/section/div/div/div/ul/li[4]/div/div/div/div[1]/div/form/fieldset/div[2]/button[2]/span"

    workplaceType_mapping = {
        'On-site': 'workplaceType-1',
        'Remote': 'workplaceType-2',
        'Hybrid': 'workplaceType-3'
    }
    workplaceType_show_result_xpath = "/html/body/div[7]/div[3]/div[4]/section/div/section/div/div/div/ul/li[7]/div/div/div/div[1]/div/form/fieldset/div[2]/button[2]/span"
     
    # TODO: DRY this up
    try:
        chosen_filters_loop('experience', experience_mapping, experience_show_result_xpath)
        print('Setting', job_filters['experience'], 'for experience')
        time.sleep(5)
    except:
        print('Could not set experience filter')
        traceback.print_exc()
        pass
    try:
        chosen_filters_loop('workplaceType', workplaceType_mapping, workplaceType_show_result_xpath)
        print('Setting', job_filters['workplaceType'], 'for workplace type')
        time.sleep(5)
    except:
        print('Could not set workplace type filter')
        traceback.print_exc()
        pass

    # TODO: finish ordering results by "Most Recent" (struggling to select "show results" button)
    # all_filters = driver.find_element(By.XPATH, "//button[text()='All filters']")
    # all_filters.click()
    # most_recent = driver.find_element(By.XPATH, "//span[text()='Most recent']")
    # most_recent.click()
    # time.sleep(10)
    # show_results = WebDriverWait(driver, 30).until(
    #     EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'results')]"))
    #         )
    # show_results.click()

def master_scraper(url, email, password, preferred_job_title, job_filters, database_connector):
    driver = get_driver()
    time.sleep(5) 

    driver.get(url)

    catch_page_redirect(driver, url)
    time.sleep(10) 
    
    cookies_loaded = load_cookies(driver)
    time.sleep(10)

    login_to_linkedin(driver, email, password, cookies_loaded)
    time.sleep(10)
    
    search_jobs(driver, preferred_job_title)
    time.sleep(5)

    set_job_filters(driver, job_filters)
    time.sleep(5)

    jobs = scrape_page(driver, database_connector)
    # TODO: build pagination function, repeat `scrape_page`

    driver.quit()

    return jobs
    
job_homepage_url = "https://www.linkedin.com/"
preferred_job_title = 'DevOps Engineer'
job_filters = {
    'experience': ['Entry level'], 
    'workplaceType': ['Hybrid']
    }

if __name__ == "__main__":
    database_connector = Database_connector()
    
    creds = database_connector.read_creds()
    email = creds['LINKEDIN_EMAIL']
    password = creds['LINKEDIN_PASSWORD']

    # Load credentials from creds.yaml
    creds = database_connector.read_creds()
    
    email = creds['LINKEDIN_EMAIL']
    password = creds['LINKEDIN_PASSWORD']

    jobs = master_scraper(
        job_homepage_url, 
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

    # print(database_connector.upload_to_db(jobs))
