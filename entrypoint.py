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


def run_script(script_name: str) -> None:
    """Runs a script based on its extension.

    Args:
        script_name (str): The name of the script to run (e.g. "testscript.sh")
    """
    script_path_base = Path(f"/code/scripts/{script_name}")
    
    ### Try different extensions
    for ext in EXTENSION_MAP.keys():
        script_path = script_path_base.with_suffix(ext)
        if script_path.exists():
            command = EXTENSION_MAP[ext] + [script_path]
            logging.info(f"----> Running {script_path}...\n")
            subprocess.run(command)
            return
    
    ### Log and handle unsupported script types
    logging.error(f"Unsupported script type for {script_name}")
    exit(1)


def convert_to_current_tz(dt: datetime) -> datetime:
    """Converts a datetime object to the current timezone.

    Args:
        dt (datetime): A datetime object

    Returns:
        datetime: The datetime object in the current timezone
    """
    current_tz = pytz.timezone(getenv("TZ", "Europe/Berlin"))
    return dt.astimezone(current_tz)


def check_file_or_folder_exists(script_name: str) -> bool:
    """Checks if a script or folder/script exists in the /code/scripts directory.

    Args:
        script_name (str): The name of the script or folder/script (e.g. "testscript")

    Returns:
        bool: True if the script or folder/script exists, False if not.
    """
    script_path_base = Path(f"/code/scripts/{script_name}")
    
    for ext in EXTENSION_MAP.keys():
        script_path = script_path_base.with_suffix(ext)
        if script_path.exists():
            return True # TODO: Return folder, name and extensions one by one
    
    logging.error(f"{script_name} doesn't seem to exist in the /code/scripts directory or it has the wrong file extension.")
    return False


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------


### Extension map for different script types
EXTENSION_MAP = {
    ".sh": ["/bin/bash"],
    ".pl": ["perl"],
    ".py": ["python3"],
}

### Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%d.%m.%Y %H:%M:%S %Z")

### Attach signal handlers for SIGTERM (docker stop)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler) ### When run with --rm and CTRL+C

### Scheduled cron job list (RS_<SCRIPT_NAME>)
cron_jobs = []

### Filter environment variables that start with "RS_"
script_list = [key[3:] for key in environ if key.startswith("RS_")]

### Display a welcoming message in Docker logs
logging.info("Container started. Welcome!\n")

logging.info("Checking if scripts and folders exist:")
all_checks_passed = True
for script_name in script_list:
    cron_expression = getenv(f"RS_{script_name}", None)
    
    ### Check if script or folder/script exists
    if "_" in script_name:
        folder, script = script_name.split("_", 1)
        script_file = f"{folder}/{script.lower()}"
    else:
        script_file = script_name.lower()

    ### Check if the file or folder exists
    if not check_file_or_folder_exists(script_file):
        all_checks_passed = False
        continue  # Skip cron check if file doesn't exist

    ### Validate the cron expression if the file/folder check passed
    if cron_expression and is_valid_cron(cron_expression):
        cron_description = get_description(cron_expression) # IndexError CAN occur here if e.g. day of week is out of range
        logging.info(f"  - {script_file}: {cron_expression} ({cron_description})")
    else:
        logging.error(f"  - {script_name}: Invalid or missing cron expression")
        all_checks_passed = False


### Only proceed if all checks are passed
if all_checks_passed:
    logging.info("All scripts, folders, and cron expressions are valid. Proceeding...\n")

    ### Determine the first script to run and print its next execution time
    for script_name in script_list:
        cron_expression = getenv(f"RS_{script_name}", None)
        script_file = script_name.lower() if "_" not in script_name else f"{script_name.split('_')[0]}/{script_name.split('_')[1].lower()}"

        next_execution_timestamp = convert_cron_to_timestamp(cron_expression)
        cron_jobs.append({
            "script_name": script_file,
            "cron_expression": cron_expression,
            "next_execution_timestamp": next_execution_timestamp
        })

    next_job = min(cron_jobs, key=lambda job: job["next_execution_timestamp"])
    next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_job["next_execution_timestamp"])).strftime("%A, %B %d, %Y %I:%M %p")
    logging.info(f"--> First execution will be {next_job['script_name']} on: {next_execution_readable}")

    ### Initialize next_execution_time
    next_execution_time = min(job["next_execution_timestamp"] for job in cron_jobs)

    ### Parallel Execution with ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        ### Endless loop
        while True:
            current_time_timestamp = datetime.now().timestamp()

            for job in cron_jobs:
                script_name = job["script_name"]
                next_execution_timestamp = job["next_execution_timestamp"]

                if current_time_timestamp >= next_execution_timestamp:
                    ### Execute script asynchronously
                    executor.submit(run_script, script_name)

                    ### Plan next execution
                    job["next_execution_timestamp"] = convert_cron_to_timestamp(job["cron_expression"])

                    ### Print next execution time
                    next_times = [job["next_execution_timestamp"] for job in cron_jobs]
                    next_execution_time = min(next_times)
                    next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_execution_time)).strftime("%A, %B %d, %Y %I:%M %p")
                    next_job = next((j for j in cron_jobs if j["next_execution_timestamp"] == next_execution_time), None)
                    if next_job:
                        logging.info(f"--> Next execution will be {next_job['script_name']} on: {next_execution_readable}")

            ### Sleep until the next scheduled execution
            sleep_duration = next_execution_time - current_time_timestamp
            sleep(max(0, sleep_duration))  # Avoid negative sleep duration
else:
    logging.error("Some scripts or cron expressions are invalid. Exiting...")
    exit(1)
