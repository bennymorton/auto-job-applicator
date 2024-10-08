import json
import math
import requests
import time
import yaml

from auto_job_applicator.db_utils import DatabaseConnector

class OpenAINotionIntegration:

    def __init__(self) -> None:
        pass    

    def get_job_insights(self, job_description, openai_api_key):
        """Feed a job description and tailored prompt into the OpenAI API.

        To get summarised insights on a specific job.

        Args:
            job_description (String): Full job description scraped from the job page
            openai_api_key (String): Self explanatory

        Returns:
            result (JSON): JSON object containing the gathered insights
        """
        print("Getting job insights using OpenAI API")
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}",
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    Given the following job description, return these insights in JSON form:
                    1. Is it a progressive workplace? (YES/NO). To be given YES for this it needs to offer hybrid or remote working, or flexible working hours.
                    2. What industry is this company in?
                    3. A list of the required tech stack elements, and required skills summarised also.

                    The JSON should be structured like this:
                        {{
                            "Progressive?": 'YES' or 'NO'. If yes, whether it was hybrid, remote working, or flexible working hours that qualified it.,
                            "Industry": The name of the top-level UK SIC sector that the company falls into, so "Financial and Insurance Activities" for example, nothing more granular, 
                            "Tech stack": [a list of the teck stack items],
                            "Required skills": [a list of the required skills]
                        }}

                    Job Description: 
                    {job_description}
                    """,
                }
            ],
            "temperature": 0.2,
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = json.loads(response.json()["choices"][0]["message"]["content"])
            time.sleep(5)
            return result
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    def calculate_interest(self, insights, preferred_tech_stack, preferred_industries):
        """Calculate how closely a job description aligns with a given a set of preferences.

        The interest being a figure in the range of 1-3.

        Args:
            insights (JSON): The output of get_job_insights
            preferred_tech_stack (List): A list of tech stack items user is interested in
            preferred_industries (_type_): A list of industries user is interested in

        Returns:
            interest (Int): A figure between 1 and 3, 3 being most aligned
        """
        interest = 1

        # Count how many items in the job's stack are in the preferred stack 
        job_tech_stack_cleaned = [item.lower().strip() for item in insights["Tech stack"]]
        preferred_tech_stack_cleaned = [
            item.lower().strip() for item in preferred_tech_stack
        ]
        matches = [
            tool for tool in job_tech_stack_cleaned if tool in preferred_tech_stack_cleaned
        ]  
        stack_match_perc = math.floor(
            (len(matches) / len(preferred_tech_stack_cleaned)) * 100
        )
        # Add interest point if more than 50%
        if stack_match_perc > 50:
            interest += 1

        # Match the industry of the job to the preferred industries
        if insights["Industry"].lower().strip() in preferred_industries:
            interest += 1
        
        # Is the job progressive? 
        # Must offer remote, hybrid working or flexible working hours to qualify this
        if "YES" in insights["Progressive?"]:
            interest += 1

        print("Interest: ", interest)
        return interest

    def extract_new_data(self, database_connector):
        """Extract newly added rows from the AWS RDS database.

        Args:
            database_connector (DatabaseConnector): The dbutils.DatabaseConnector class instance 

        Returns:
            new_jobs (List): A list of the jobs newly added to the database
        """
        print("Querying database for newly added jobs")
        sql_output = database_connector.query_db(
            "SELECT * FROM bens_jobs WHERE in_notion = 'FALSE'"
        )
        new_jobs = []
        for row in sql_output:
            new_jobs.append(dict(row._mapping))
        print("Found " + str(len(new_jobs)) + " new jobs")
        return new_jobs

    def send_to_notion(self, job, insights, notion_api_key):
        """Send jobs extracted from the RDS database to Notion page, 
         
        using the Notion API.

        Args:
            job (Dict): Details of a single job
            insights (JSON): Insights about the job returned by the OpenAI API
            notion_api_key (String): Self explanatory

        Returns:
            new_jobs (List): A list of the jobs newly added to the database
        """
        print("Sending new job to notion")
        headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        new_job_payload = f"""{{
            "parent": {{
                "type": "database_id",
                "database_id": "2d16928a6f8844c5a6a1f32f2d426d2e"
            }},
            "properties": {{
                "Company Name": {{
                    "type": "title",
                    "title": [
                        {{
                            "type": "text",
                            "text": {{
                                "content": "{job['company_name']}"
                            }}
                        }}
                    ]
                }},
                "Job Title": {{
                    "type": "rich_text",
                    "rich_text": [
                        {{
                            "type": "text",
                            "text": {{
                                "content": "{job['job_title']}"
                            }}
                        }}
                    ]
                }},
                "Interest": {{
                    "type": "number",
                    "number": {job['interest']}
                }},
                "Job Link": {{
                    "type": "url",
                    "url": "{job['job_link']}"
                }},
                "Industry": {{
                    "type": "rich_text",
                    "rich_text": [
                        {{
                            "type": "text",
                            "text": {{
                                "content": "{job['industry']}"
                            }}
                        }}
                    ]
                }},
                "Progressive?": {{
                    "type": "rich_text",
                    "rich_text": [
                        {{
                            "type": "text",
                            "text": {{
                                "content": "{job['progressive']}"
                            }}
                        }}
                    ]
                }}
            }}
        }}"""
        # POST the new job details to the database as row attributes
        pages_url = "https://api.notion.com/v1/pages"
        new_page_response = requests.post(pages_url, headers=headers, data=new_job_payload)

        if new_page_response.status_code == 200:
            print("New job added successfully: \n", job["job_id"])
        else:
            print(f"Error: {new_page_response.status_code}")
            print(new_page_response.text)

        # PATCH the tech stack and required skills to the specific job page content
        tech_stack = ", ".join(insights["Tech stack"])
        required_skills = ", ".join(insights["Required skills"])
        update_job_payload = f"""{{
            "children": [
    		    {{
                    "object": "block",
    			    "type": "paragraph",
    			    "paragraph": {{
    				    "rich_text": [
                            {{
                                "type": "text", 
                                "text": {{
                                    "content": "Tech stack: "
                                    }},
                                "annotations": {{
                                    "bold": true,
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false,
                                    "code": false,
                                    "color": "default"
                                }}
                            }},
                            {{
                                "type": "text", 
                                "text": {{"content": "{tech_stack}"}},
                                "annotations": {{
                                    "bold": false,
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false,
                                    "code": false,
                                    "color": "default"
                                }}
                            }}

                        ]
    			    }}
    		    }},
                {{
                    "object": "block",
    			    "type": "paragraph",
    			    "paragraph": {{
    				    "rich_text": [
                            {{
                                "type": "text", 
                                "text": {{
                                    "content": "Required skills: "
                                    }},
                                "annotations": {{
                                    "bold": true,
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false,
                                    "code": false,
                                    "color": "default"
                                }}
                            }},
                            {{
                                "type": "text", 
                                "text": {{"content": "{required_skills}"}},
                                "annotations": {{
                                    "bold": false,
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false,
                                    "code": false,
                                    "color": "default"
                                }}
                            }}

                        ]
    			    }}
    		    }}
            ]
        }}"""
        new_page_id = new_page_response.json()["id"]
        block_url = f"https://api.notion.com/v1/blocks/{new_page_id}/children"
        update_page_response = requests.patch(
            block_url, headers=headers, data=update_job_payload
        )


def main():
    """High level function to create the requisite classes, then run scraping methods."""
    database_connector = DatabaseConnector()
    openai_notion_integration = OpenAINotionIntegration()
    creds = database_connector.read_creds()

    new_jobs = openai_notion_integration.extract_new_data(database_connector)
    for job in new_jobs:
        print("New job: ", job["job_id"])
        insights = openai_notion_integration.get_job_insights(job["job_description"], creds["OPENAI_API_KEY"])
        interest = openai_notion_integration.calculate_interest(
            insights, preferred_tech_stack, preferred_industries
        )
        # Add AI insights to job info
        job["industry"] = insights["Industry"]
        job["progressive"] = insights["Progressive?"]
        job["interest"] = interest

        openai_notion_integration.send_to_notion(job, insights, creds["NOTION_API_KEY"])

        # In DB mark job as added to notion
        job_id = job["job_id"]
        sql_string = (
            f"UPDATE bens_jobs SET in_notion = 'TRUE' WHERE job_id = '{job_id}';"
        )
        database_connector.query_db(sql_string)
        print("#############################")


if __name__ == "__main__":
    # User defined details
    preferred_tech_stack = [
        "Docker",
        "Terraform",
        "Kubernetes",
        "Helm",
        "Networking",
        "Python",
        "SQL",
        "git",
        "Databricks",
        "Kafka",
        "Spark",
        "Airflow",
        "AWS",
        "git",
    ]
    preferred_industries = [
        "fintech",
        "climate",
        "telecommunications, media, and technology",
    ]
    main()
