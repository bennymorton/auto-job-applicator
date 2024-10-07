import json
import math
import requests
import time
from db_utils import Database_connector

def get_job_insights(job_description, openai_api_key):
    print('Getting job insights using OpenAI API')
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {openai_api_key}"
    }
    # TODO: regulate industry to be from a set list
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": f"""
                Given the following job description, return these insights in JSON form:
                1. Is it a progressive workplace? (YES/NO). To be given YES for this it needs to offer hybrid or remote working, or flexible working hours.
                2. What industry is this company in?
                3. A list of the required tech stack elements, and required skills summarised also.
             
                The JSON should be structured like this:
                    {{
                        "Progressive?": 'YES' or 'NO'. If yes, whether it was hybrid, remote working, or flexible working hours that qualified it.,
                        "Industry": '<the industry>', 
                        "Tech stack": [a list of the teck stack items],
                        "Required skills": [a list of the required skills]
                    }}

                Job Description: 
                {job_description}
                """}
        ],
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = json.loads(response.json()['choices'][0]['message']['content'])
        time.sleep(5)
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def calculate_interest(insights, preferred_tech_stack, preferred_industries):
    print('Calculating job interest')
    interest = 1

    # Count how many items in the jobs stack are in the preferred stack
    job_tech_stack_cleaned = [item.lower().strip() for item in insights['Tech stack']]
    preferred_tech_stack_cleaned = [item.lower().strip() for item in preferred_tech_stack]
    matches = [tool for tool in job_tech_stack_cleaned if tool in preferred_tech_stack_cleaned] # TODO: use this later in the notion page content
    stack_match_perc = math.floor((len(matches) / len(preferred_tech_stack_cleaned)) * 100)

    if stack_match_perc > 50: # adjust interest figure accordingly
        interest += 1

    # Match the industry of the job to the preferred industries
    if insights['Industry'].lower().strip() in preferred_industries:
        aligned_industry = True
    else:
        aligned_industry = False

    if aligned_industry == True: # adjust interest figure accordingly
        interest += 1
    
    if "YES" in insights['Progressive?']: # calculate final interest figure 
        interest += 1

    print('Interest: ', interest)
    return interest

def extract_new_data(database_connector):
    print('Querying database for newly added jobs')
    sql_output = database_connector.query_db("SELECT * FROM bens_jobs WHERE in_notion = 'FALSE'")
    new_jobs = []
    for row in sql_output:
        new_jobs.append(dict(row._mapping))
    print('Found ' + str(len(new_jobs)) + ' new jobs')
    return new_jobs

def send_to_notion(job, notion_api_key):
    print('Sending new job to notion')
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
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

    pages_url = "https://api.notion.com/v1/pages"
    new_page_response = requests.post(pages_url, headers=headers, data=new_job_payload)

    if new_page_response.status_code == 200:
        print("New job added successfully: \n", job['job_id'])
    else:
        print(f"Error: {new_page_response.status_code}")
        print(new_page_response.text)

    # TODO: make this easily glancable job info look pretty in notion
    # page_info = str(json_insights['Tech stack']) + "\n" + str(json_insights['Required skills'])
    # update_job_payload = f"""{{
    #     "children": [
	# 	    {{
    #             "object": "block",
	# 		    "type": "paragraph",
	# 		    "paragraph": {{
	# 			    "rich_text": [
    #                     {{
    #                         "type": "text", 
    #                         "text": {{"content": "{page_info}"}}
    #                     }}
    #                 ]
	# 		    }}
	# 	    }}
    #     ]
    # }}"""
    # block_url = f"https://api.notion.com/v1/blocks/{job_page_id}/children"
    # print(block_url)
    # update_page_response = requests.patch(block_url, headers=headers, data=update_job_payload)
    # print(update_page_response.text)

def main():
    database_connector = Database_connector()
    # Load credentials from creds.yaml
    creds = database_connector.read_creds()

    new_jobs = extract_new_data(database_connector)
    for job in new_jobs:
        print('New job: ', job['job_id'])
        insights = get_job_insights(job['job_description'], creds['OPENAI_API_KEY'])
        interest = calculate_interest(insights, preferred_tech_stack, preferred_industries)

        # Add AI insights to job info
        job['industry'] = insights['Industry']
        job['progressive'] = insights['Progressive?']
        job['interest'] = interest

        send_to_notion(job, creds['NOTION_API_KEY'])

        # In DB mark job as added to notion 
        job_id = job["job_id"]
        sql_string = f"UPDATE bens_jobs SET in_notion = 'TRUE' WHERE job_id = '{job_id}';"
        database_connector.query_db(sql_string)
        print("#############################")


if __name__ == "__main__":
    preferred_tech_stack = [
        'Docker',
        'Terraform',
        'Kubernetes',
        'Helm',
        'Networking',
        'Python',
        'SQL',
        'git',
        'Databricks',
        'Kafka',
        'Spark',
        'Airflow',
        'AWS'

    ]
    preferred_industries = [
        'fintech',
        'climate',
        'telecommunications, media, and technology'
    ]

    main()


    