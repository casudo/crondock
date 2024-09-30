import subprocess
import pytz
import logging
import signal
import concurrent.futures
from sys import exit
from os import getenv, environ
from time import sleep
from croniter import croniter, CroniterBadCronError, CroniterBadDateError
from datetime import datetime
from cron_descriptor import get_description
from pathlib import Path


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------

__version__ = getenv("REACT_APP_VERSION", "Warning: Couldn't load version")

### Extension map for different script types
EXTENSION_MAP = {
    ".sh": ["/bin/bash"],
    ".pl": ["perl"],
    ".py": ["python3"],
}


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------


def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}. Exiting gracefully...")
    exit(1)


def convert_cron_to_timestamp(cron_expression: str) -> float:
    """Converts a cron expression to a timestamp.

    Args:
        cron_expression (str): A cron expression (e.g. "*/5 * * * *")

    Returns:
        float: The timestamp of the next execution (e.g. 1634026800.0)
    """
    current_time = datetime.now()
    cron = croniter(cron_expression, current_time)
    next_execution = cron.get_next(datetime)
    return next_execution.timestamp()


def is_valid_cron(cron_expression: str) -> bool:
    """Validates a cron expression.

    Args:
        cron_expression (str): A cron expression (e.g. "*/5 * * * *")

    Returns:
        bool: True if the cron expression is valid, False if not.
    """
    try:
        croniter(cron_expression)
        return True
    except (CroniterBadCronError, CroniterBadDateError) as e:
        logging.error(f"Invalid cron expression '{cron_expression}': {str(e)}")
        return False


def convert_to_current_tz(dt: datetime) -> datetime:
    """Converts a datetime object to the current timezone.

    Args:
        dt (datetime): A datetime object

    Returns:
        datetime: The datetime object in the current timezone
    """
    current_tz = pytz.timezone(getenv("TZ", "Europe/Berlin"))
    return dt.astimezone(current_tz)


def parse_cron_env_variable(env_value: str):
    """Parses a cron environment variable to extract cron expression, script path, and parameters.

    Args:
        env_value (str): The value of the environment variable.

    Returns:
        dict: Contains 'cron_expression', 'script_path', 'parameters'
    """
    parts = env_value.split("!")
    cron_expression = parts[0].strip() if len(parts) > 0 else None
    script_path_full = parts[1].strip() if len(parts) > 1 else None
    parameters = parts[2].strip().split() if len(parts) > 2 else []
    
    return {
        "cron_expression": cron_expression,
        "script_path_full": script_path_full,
        "parameters": parameters
    }


def run_script(script_path_relative: str, script_path_full: str, parameters: list) -> None:
    """Runs the script with optional parameters using the appropriate interpreter.

    Args:
        script_path (str): The path to the script.
        parameters (list): List of parameters to pass to the script.
    """
    script_path_obj = Path(script_path_full)
    
    if script_path_obj.exists():
        # Determine the interpreter based on the file extension
        command = []
        for ext, interpreter in EXTENSION_MAP.items():
            if script_path_obj.suffix == ext:
                command = interpreter + [str(script_path_obj)] + parameters
                break
        
        if command and parameters:
            logging.info(f"Running script: {script_path_relative} with parameters: {' '.join(parameters)}")
            subprocess.run(command)
        elif command:
            logging.info(f"Running script: {script_path_relative}")
            subprocess.run(command)
        else:
            logging.error(f"Unsupported script extension for script: {script_path_relative}")
    else:
        logging.error(f"Script not found: {script_path_relative}")


def load_cron_jobs() -> list:
    """Loads cron jobs from environment variables.

    Returns:
        list: A list of cron jobs with script path, parameters, cron expression, and next execution timestamp.
    """
    cron_jobs = []

    logging.info("Installed cron jobs:")

    ### Loop through all environment variables
    for env_key, env_value in environ.items():
        ### Check only relevant environment variables
        if env_key.startswith("RS_CRON_"):
            job_info = parse_cron_env_variable(env_value) # Cron expression, script path, parameters
            ### TODO: "cron_expression, script_path, parameters = parse_cron_env_variable(env_value)" instead? 
            cron_expression = job_info["cron_expression"]
            script_path_full = job_info["script_path_full"]
            script_path_relative = job_info["script_path_full"].replace("/code/scripts/", "../")
            parameters = job_info["parameters"]

            if not script_path_relative or not is_valid_cron(cron_expression): ### TODO: Check if path exists here
                logging.error(f"Invalid configuration for {env_key}. Skipping.")
                continue

            ### Log loaded cron job
            cron_description = get_description(cron_expression)
            logging.info(f" - {script_path_relative}: {cron_expression} ({cron_description})")
            if parameters:
                logging.info(f"     - Parameters: {' '.join(parameters)}")

            next_execution_timestamp = convert_cron_to_timestamp(cron_expression)
            cron_jobs.append({
                "script_path_full": script_path_full,
                "script_path_relative": script_path_relative,
                "parameters": parameters,
                "cron_expression": cron_expression,
                "next_execution_timestamp": next_execution_timestamp
            })
    
    return cron_jobs


def execute_cron_jobs(cron_jobs: list) -> None:
    """Executes the cron jobs in parallel.

    Args:
        cron_jobs (list): A list of cron jobs with script path, parameters, cron expression, and next execution timestamp.
    """
    ### Log first execution time
    next_job = min(cron_jobs, key=lambda job: job["next_execution_timestamp"])
    next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_job["next_execution_timestamp"])).strftime("%d.%m.%Y %H:%M:%S %Z")
    logging.info(f"--> First execution will be: {next_job['script_path_relative']} at: {next_execution_readable}")

    ### Parallel Execution with ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        ### Endless loop
        while True:
            current_time_timestamp = datetime.now().timestamp()
       
            for job in cron_jobs:
                next_execution_timestamp = job["next_execution_timestamp"]

                if current_time_timestamp >= next_execution_timestamp:
                    ### Execute script asynchronously
                    executor.submit(run_script, job["script_path_relative"], job["script_path_full"], job["parameters"])

                    ### Plan next execution
                    job["next_execution_timestamp"] = convert_cron_to_timestamp(job["cron_expression"])

                    ### Log next execution time
                    next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_job["next_execution_timestamp"])).strftime("%d.%m.%Y %H:%M:%S %Z")
                    logging.info(f"--> Next execution: {next_job['script_path_relative']} at: {next_execution_readable}")

            ### Calculate sleep duration
            next_execution_time = min(job["next_execution_timestamp"] for job in cron_jobs)
            sleep_duration = next_execution_time - current_time_timestamp
            sleep(max(0, sleep_duration))


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ### Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%d.%m.%Y %H:%M:%S %Z")
    
    ### Attach signal handlers for SIGTERM (docker stop)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler) ### When run with --rm and CTRL+C

    logging.info("Container started. Welcome!\n")

    cron_jobs = load_cron_jobs()
    
    if cron_jobs:
        logging.info("All scripts, folders, and cron expressions are valid. Proceeding...\n")
        execute_cron_jobs(cron_jobs)
    else:
        logging.error("No valid cron jobs found. Exiting...")
        exit(1)
