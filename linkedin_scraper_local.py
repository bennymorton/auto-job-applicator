import pickle
import re
import subprocess
import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from webdriver_manager.firefox import GeckoDriverManager

from db_utils import DatabaseConnector


class Scraper:
    """Scraper class containing all requisite methods to log in to, 
    then scrape specific tailored jobs from LinkedIn
    """

    def __init__(self) -> None:
        self.database_connector = DatabaseConnector()

    def get_driver(self) -> webdriver.Firefox:
        """Install and build the latest version of the Selenium Firefox driver.

        Returns:
            webdriver.Firefox: Driver object
        """
        firefox_driver_install = GeckoDriverManager().install()

        # Get and print the driver version from subprocess version command
        try:
            version_output = subprocess.check_output(
                [firefox_driver_install, "--version"], stderr=subprocess.STDOUT
            ).decode("utf-8")
        except Exception as error:
            print(f"Error fetching FirefoxDriver version: {error}")
        else:
            print(f"Installed FirefoxDriver version: {version_output}")
            print("############################")

        # Build Firefox driver
        options = Options()
        options.add_argument("--no-sandbox")
        driver = webdriver.Firefox(
            service=FirefoxService(firefox_driver_install), options=options
        )
        return driver

    def catch_page_redirect(self, driver, url) -> None:
        """Checks whether the page loaded by the driver is correct.

        Often dynamic websites will redirect from a given URL to
        a different webpage, for example to force you to log in
        via a certain route.

        Args:
            driver (webdriver.Firefox): Driver object
            url (String): The website URL
        """
        counter = 0
        while counter <= 10:
            print("Checking we're on the correct page...")
            if driver.current_url == url:
                print("We are!")
                break
            else:
                print("Page redirect has occurred. Restarting driver.")
                counter += 1
                driver.quit()
                time.sleep(5)
                driver = self.get_driver()
                time.sleep(5)
                driver.get(url)
                time.sleep(5)
    
    def load_cookies(self, driver) -> bool:
        """Load webpage cookies from external cookies pickle file.

        Args:
            driver (webdriver.Firefox): Driver object

        Returns:
            Boolean: Denotes whether the cookies have loaded or not
        """
        print("Attempting to load cookies to bypass full sign in")
        cookies = pickle.load(
            open(
                "/Users/benmorton/Desktop/project_files/auto_job_applicator/cookies.pkl",
                "rb",
            )
        )
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as error:
                print("Failed to load cookie. Error: ", error)
                return False
        print("Cookies loaded")
        return True
    
    def login_to_linkedin(self, driver, email, password, cookies_loaded) -> bool:
        """Procedure to log into LinkedIn with given credentials, as follows:

        1. Close Google signin modal
        2. Load cookies from external pickle file
        3. Click sign in button
        4. Proceed to enter log in credentials and sign in
        5. Check for day ruining verification captcha (immediately ends whole script)
        6. Load fresh cookies into pickle file for next run

        Args:
            driver (_type_): _description_
            email (_type_): _description_
            password (_type_): _description_
            cookies_loaded (_type_): _description_
        """
        self._close_google_modal(driver)
        self._interact_with_element(driver, By.LINK_TEXT, "Sign in", "click")

        try:
            name_element = driver.find_element(By.CLASS_NAME, "profile__identity")
        except:
            pass
        if (cookies_loaded is True) and (name_element):
            pass
        else:
            self._interact_with_element(driver, By.ID, "username", email)
        self._interact_with_element(driver, By.ID, "password", password)
        self._interact_with_element(driver, By.XPATH, "//button[@type='submit']", "click")

        if "challenge" in driver.current_url:
            print("Verification Captcha occurred. Needs human intervention.")
            return False
        
        print("Successfully signed in!")
        # Get cookies and save into a pickle file
        cookies = driver.get_cookies()
        with open(
            "/Users/benmorton/Desktop/project_files/auto_job_applicator/cookies.pkl",
            "wb",
        ) as file:
            pickle.dump(cookies, file)
        return True
    
    @staticmethod
    def _close_google_modal(driver) -> None:
        """Helper method to close the Google sign in modal, 
        
        because it blocks the actual LinkedIn sign in button
        """
        try:
            google_modal_iframe = driver.find_element(By.CSS_SELECTOR, "iframe")
            # Switch to iframe containing the Google sign in modal
            driver.switch_to.frame(google_modal_iframe)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "close"))
            ).click()
        except:
            print("Could not find Google Sign in modal")
        else:
            print("Closing Google Sign in modal")
            # Switch back to the main page driver context (not the iframe)
            time.sleep(10)
        finally:
            driver.switch_to.default_content()

    def _interact_with_element(self, driver, selector, locator, input) -> WebElement:
        """Helper method to use Selenium explicit Wait to select a given element.

        Then either click or enter text if it is an input field.

        Args:
            driver (webdriver.FireFox): Firefox driver object
            selector (Selenium By object): The method by which to select the element
                I.E. By.ID, By.XPATH .etc.
            locator (String): The corresponding string to locate
                the element within the page's HTML
            input (String): "click" if the element is to be clicked.
                If it is a text input field, the text to be inputted.

        Returns:
            _type_: _description_
        """
        try:
            element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        selector,
                        locator,
                    )
                )
            )
        except TimeoutException:
            print('Timed out trying to find the element, try again later. Details:')
            print(selector, " ", locator)
            return None
        
        if input == "click":
            element.click()
        else:
            element.send_keys(input)
        return element

    def search_jobs(self, driver, preferred_job_title) -> bool:
        """Navigate to LinkedIn jobs page, 
        
        find search bar and search for given job title

        Args:
            driver (webdriver.FireFox): Firefox driver object
            preferred_job_title (String): User inputted preferred job title to search for
        """
        # Navigate to jobs page
        print("Navigating to jobs page")
        self._interact_with_element(driver, By.CSS_SELECTOR, "li.global-nav__primary-item:nth-child(3) > a:nth-child(1)", "click")
        
        # Select jobs search bar
        # jobs_search_bar = self._interact_with_element(driver, By.XPATH,
        #             "/html/body/div[7]/header/div/div/div/div[2]/div[2]/div/div/label/following-sibling::input[1]", "click")
        jobs_search_bar = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (
                        By.CLASS_NAME,
                        "jobs-search-box__keyboard-text-input"
                    )
                )
            )
        time.sleep(3)
        jobs_search_bar.click()
        if jobs_search_bar is None:
            driver.quit()
            return False
        
        time.sleep(5)
        jobs_search_bar.send_keys(preferred_job_title)
        jobs_search_bar.send_keys(Keys.ENTER)

    def set_job_filters(self, driver, job_filters):
        """Select and choose the given filters:

        - Experience Level
        - Workplace type

        Args:
            driver (webdriver.FireFox): Firefox driver object
            job_filters (Dict): Dictionary of user-defined job filters to apply
        """
        print("Setting job filters")

        def _chosen_filters_loop(filter, filter_mapping, show_result_xpath) -> None:
            """Internal helper method to loop through and apply given filter selection"""
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.ID, ("searchFilter_" + filter)))
            ).click()

            for choice in job_filters[filter]:
                dynamic_xpath = (
                    f"//*[@id='{filter_mapping[choice]}']/following-sibling::label[1]"
                )
                try:
                    element = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, dynamic_xpath))
                    )
                    element.click()
                    time.sleep(5)
                except Exception as e:
                    print("Could not select filter for", filter, "-", choice)
                    print("Attempted XPATH:\n", dynamic_xpath)
                    print(repr(e))
                    traceback.print_exc()

                element = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, show_result_xpath))
                    )
                element.click()

        # Map dynamically inputted filters to corresponding CSS IDs
        experience_mapping = {
            "Internship": "experience-1",
            "Entry level": "experience-2",
            "Associate": "experience-3",
            "Mid-Senior level": "experience-4",
            "Directory": "experience-5",
            "Executive": "experience-6",
        }
        experience_show_result_xpath = "/html/body/div[7]/div[3]/div[4]/section/div/section/div/div/div/ul/li[4]/div/div/div/div[1]/div/form/fieldset/div[2]/button[2]/span"

        workplace_type_mapping = {
            "On-site": "workplaceType-1",
            "Remote": "workplaceType-2",
            "Hybrid": "workplaceType-3",
        }
        workplace_type_show_result_xpath = "/html/body/div[7]/div[3]/div[4]/section/div/section/div/div/div/ul/li[7]/div/div/div/div[1]/div/form/fieldset/div[2]/button[2]/span"

        try:
            _chosen_filters_loop(
                "experience", experience_mapping, experience_show_result_xpath
            )
            print("Setting", job_filters["experience"], "for experience")
            time.sleep(5)
        except:
            print("Could not set experience filter")
            traceback.print_exc()
        try:
            _chosen_filters_loop(
                "workplaceType", workplace_type_mapping, workplace_type_show_result_xpath
            )
            print("Setting", job_filters["workplaceType"], "for workplace type")
            time.sleep(5)
        except:
            print("Could not set workplace type filter")
            traceback.print_exc()

    def scrape_page(self, driver) -> list:
        """One by one, scrape all the jobs from a page.

        Args:
            driver (webdriver.Firefox): Driver object

        Returns:
            list: A list of the scraped jobs from one page
        """
        jobs = []
        job_ids = []
        # Get and count each of the individual job_card containers
        job_cards = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "jobs-search-results__list-item")
            )
        )
        print("Found " + str(len(job_cards)) + " jobs total. Extracting info now.")

        for index, job_card in enumerate(job_cards):
            try:
                job_card.click()
                time.sleep(10)
                job_dict = self.scrape_job(driver, job_card, job_ids)
            except TimeoutError:
                traceback.print_exc()
                print("Timed out trying to scrape the details of a job.")
                continue
            except Exception as e:
                print(f"Error extracting job details: {e}")
                traceback.print_exc()
                continue
            else:
                # If the job already exists in the database or has been scraped in this round
                if job_dict is None:
                    continue
                jobs.append(job_dict)
                job_ids.append(job_dict["job_id"])
                print(
                    str(index + 1)
                    + ". Scraped new job: "
                    + job_dict["job_title"]
                    + " at "
                    + job_dict["company_name"]
                )

        print("Scraped " + str(len(jobs)) + " new jobs.")
        return jobs

    def scrape_job(self, driver, job_card, job_ids) -> dict | None:
        """Scrape and format the title, company, location, description and URL from
            a single listed job.

        Args:
            driver (webdriver.Firefox): Driver object
            job_card (Selenium WebElement): The Selenium element containing
                the HTML for a single job
            job_ids (List): A cumulative list of the job_ids scraped
                in this round so far
            database_connector (Class): The methods needed to connect to and
                interact with the database

        Returns:
            job_dict Dict: A dictionary containing the details of a single job
        """
        job_title = self._scrape_job_title(driver)
        company_name = self._scrape_job_text(
            driver,
            ".job-details-jobs-unified-top-card__company-name > a:nth-child(1)",
        )
        job_id = self._validate_new_job(job_title, company_name, job_ids)
        # If this job is a duplicate or it already exists in the DB, do not proceed
        if job_id:
            pass
        else:
            return None

        location = self._scrape_job_location(driver)
        job_link = self._scrape_job_link(driver)
        job_description = self._scrape_job_text(
            driver, "div.jobs-description__content"
        )
        job_dict = {
            "job_id": job_id,
            "job_title": job_title,
            "company_name": company_name,
            "location": location,
            "job_link": job_link,
            "job_description": job_description,
            "in_notion": False,
        }
        return job_dict

    def _scrape_job_title(self, driver) -> str:
        """Helper method. Select job title then use regex to remove the repeating part"""
        job_title_raw = self._scrape_job_text(
            driver, "a.job-card-list__title"
        )
        match = re.match(r"(.+?)\s*\1.*", job_title_raw)
        if match:
            job_title = match.group(1).strip()
        else:
            job_title = job_title_raw.strip()
        return job_title

    @staticmethod
    def _scrape_job_text(driver, locator) -> str:
        """Generic helper method to scrape a given text element detail from the listed job.

        Utilising an explicit Selenium Wait creates more robust web scraping,
        by making sure the element has loaded first before attempting to select it.
        """
        try:
            text = (
                WebDriverWait(driver, 10)
                .until(EC.presence_of_element_located((By.CSS_SELECTOR, locator)))
                .text.strip()
            )
        except TimeoutException:
            print("Timed out trying to locate the element:")
            print(locator)
        else:
            return text

    @staticmethod
    def _scrape_job_location(driver) -> str:
        """Helper method. Scrapes the job location."""
        location_wrapper = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".job-details-jobs-unified-top-card__primary-description-container",
                )
            )
        )
        location = location_wrapper.find_element(
            By.CLASS_NAME, "tvm__text"
        ).text.strip()
        return location

    @staticmethod
    def _scrape_job_link(driver) -> str:
        """Helper method. Scrape the specific job page URL."""
        link = (
            WebDriverWait(driver, 10)
            .until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a.job-card-list__title")
                )
            )
            .get_attribute("href")
        )
        return link

    def _validate_new_job(self, job_title, company_name, job_ids) -> str | bool:
        """Generate unique job ID and query DB to see if it already exists.
        Very often there are duplicate jobs listed.
        """
        job_id = (job_title + company_name).replace(" ", "_")
        sql_string = f"SELECT * FROM bens_jobs WHERE job_id = '{job_id}'"
        sql_output = self.database_connector.query_db(sql_string)
        row = sql_output.fetchone()
        # If there is no row in the DB with the given ID, and it has not yet
        # been scraped this round, then proceed with scraping
        if (row is None) and (job_id not in job_ids):
            print("Found new job: ", job_id)
            return job_id
        return False

    def master_scraper(self, email, password, preferred_job_title, job_filters):
        """Main method by which to successively run 
        all the other scraper methods in the required order.

        Args:
            email (String): User inputted Linkedin email login
            password (String): User inputted Linkedin password login
            preferred_job_title (String): User inputted job title to search for
            job_filters (List): User inputted preferred job filters

        Returns:
            jobs (List): All the scraped job details
        """
        driver = self.get_driver()
        time.sleep(5)

        url = "https://www.linkedin.com/"
        driver.get(url)

        self.catch_page_redirect(driver, url)

        cookies_loaded = self.load_cookies(driver)
        time.sleep(5)

        login_result = self.login_to_linkedin(driver, email, password, cookies_loaded)
        if login_result is False:
            return None
        time.sleep(5)
        
        jobs_search_result = self.search_jobs(driver, preferred_job_title)
        if jobs_search_result is False:
            return
        self.set_job_filters(driver, job_filters)

        jobs_list = self.scrape_page(driver)

        driver.quit()
        return jobs_list


def main(preferred_job_title, job_filters) -> None:
    """High level function to create the requisite classes, then run scraping methods."""
    database_connector = DatabaseConnector()
    creds = database_connector.read_creds()
    email = creds["LINKEDIN_EMAIL"]
    password = creds["LINKEDIN_PASSWORD"]

    scraper = Scraper()
    counter = 0
    while counter < 10:
        counter += 1
        jobs = scraper.master_scraper(email, password, preferred_job_title, job_filters)
        if jobs:
            break
    
    try:
        database_connector.upload_to_db(jobs)
        print("Newly scraped jobs uploaded to database!")
    except Exception as e:
        print(repr(e))


if __name__ == "__main__":
    # User input details
    preferred_job_title = "DevOps Engineer"
    job_filters = {"experience": ["Entry level"], "workplaceType": ["Hybrid"]}
    main(preferred_job_title, job_filters)
