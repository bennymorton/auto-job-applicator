import yaml
from sqlalchemy import create_engine
from sqlalchemy.sql import text

class Database_connector:
    def __init__(self) -> None:
        pass

    def read_db_creds(self):
        with open('auto_job_applicator/db_creds.yaml', 'r') as db_creds_file:
            db_creds = yaml.safe_load(db_creds_file)
        return db_creds     

    def init_db_engine(self):
        db_creds = self.read_db_creds()

        DATABASE_TYPE = db_creds['DATABASE_TYPE']
        DBAPI = db_creds['DBAPI']
        HOST = db_creds['HOST']
        USER = db_creds['USER']
        PASSWORD = db_creds['PASSWORD']
        DATABASE = db_creds['DATABASE']
        PORT = db_creds['PORT']

        engine = create_engine(f"{DATABASE_TYPE}+{DBAPI}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")
        return engine
    
    def upload_to_db(self, jobs):
        engine = self.init_db_engine()
        with engine.begin() as connection:
            sql_output = connection.execute(
                text("INSERT INTO bens_jobs (job_id, job_title, company_name, location, job_link, job_description, in_notion) VALUES (:job_id, :job_title, :company_name, :location, :job_link, :job_description, :in_notion)"),
                jobs
            )

            return sql_output
        
    def query_db(self, sql_string):
        engine = self.init_db_engine()
        with engine.begin() as connection:
            sql_output = connection.execute(text(sql_string))
        return sql_output   
    

