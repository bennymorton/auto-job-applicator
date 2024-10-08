import yaml

from sqlalchemy import create_engine
from sqlalchemy.sql import text


class DatabaseConnector:
    """A collection of methods to connect and interact with an AWS RDS database."""

    def __init__(self) -> None:
        pass

    def read_creds(self):
        """Read in the external credentials file.

        Returns:
            YAML: YAML file containing the database and sign in credentials
        """
        with open("creds.yaml", "r") as creds_file:
            creds = yaml.safe_load(creds_file)
        return creds

    def init_db_engine(self):
        """Generate a SQLAlchemy Engine to interact with the database.

        Returns:
            SQLAlchemy Engine: See above
        """
        db_creds = self.read_creds()

        DATABASE_TYPE = db_creds["DATABASE_TYPE"]
        DBAPI = db_creds["DBAPI"]
        HOST = db_creds["HOST"]
        USER = db_creds["USER"]
        PASSWORD = db_creds["PASSWORD"]
        DATABASE = db_creds["DATABASE"]
        PORT = db_creds["PORT"]

        engine = create_engine(
            f"{DATABASE_TYPE}+{DBAPI}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
        )
        return engine

    def upload_to_db(self, jobs):
        """Use the generated engine to upload a collection of rows to the database

        Args:
            jobs (List): A list of dictionaries of the scraped job details

        Returns:
            SQLAlchemy Cursor object: The output of the given SQL query
        """
        engine = self.init_db_engine()
        with engine.begin() as connection:
            sql_output = connection.execute(
                text(
                    "INSERT INTO bens_jobs (job_id, job_title, company_name, location, job_link, job_description, in_notion) VALUES (:job_id, :job_title, :company_name, :location, :job_link, :job_description, :in_notion)"
                ),
                jobs
            )
            return sql_output

    def query_db(self, sql_string):
        """Using the SQLALchemy enging, query the database with a given SQL string.

        Args:
            sql_string (String): A fully formatted ready to query SQL string

        Returns:
             SQLAlchemy Cursor object: The output of the given SQL query
        """
        engine = self.init_db_engine()
        with engine.begin() as connection:
            sql_output = connection.execute(text(sql_string))
        return sql_output
