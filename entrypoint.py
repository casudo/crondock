import subprocess
import pytz
from os import getenv, environ
from time import sleep
from croniter import croniter, CroniterBadCronError, CroniterBadDateError
from datetime import datetime
from cron_descriptor import get_description
from pathlib import Path


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------


### Convert cron expression to timestamp
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


### Validate cron expression
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
    except (CroniterBadCronError, CroniterBadDateError):
        return False
    

### Run script function
def run_script(script_name: str) -> None:
    """Runs a script.

    Args:
        script_name (str): The name of the script to run (e.g. "testscript.sh")
    """
    print(f"----> Running {script_name}...\n")
    script_path = f"/code/{script_name}"
    if script_name.endswith(".sh"):
        subprocess.run([script_path])
    elif script_name.endswith(".pl"):
        subprocess.run(["perl", script_path])
    elif script_name.endswith(".py"):
        subprocess.run(["python3", script_path])
    else:
        print(f"Unsupported script type for {script_name}")


def convert_to_current_tz(dt: datetime) -> datetime:
    """Converts a datetime object to the current timezone.

    Args:
        dt (datetime): A datetime object

    Returns:
        datetime: The datetime object in the current timezone
    """
    current_tz = pytz.timezone(getenv("TZ", "Europe/Berlin"))
    return dt.astimezone(current_tz)


### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------
### ----------------------------------------------------------------------------------------------------------


### Scheduled cron job list (RS_<SCRIPT_NAME>)
cron_jobs = []

### Filter environment variables that start with "RS_"
script_list = [key[3:] for key in environ if key.startswith("RS_")]

### Display a welcoming message in Docker logs
print("\nContainer started. Welcome!")
# print("⏳ Checking environment variables...")

print("\nScripts and their cron expressions:")
for script_name in script_list:
    cron_expression = getenv(f"RS_{script_name}", None)
    if cron_expression and is_valid_cron(cron_expression):
        script_file = script_name.lower()  # Assumption: script names are in lowercase
        
        ### Determine the script type by checking the /code directory
        script_path = Path("/code")
        found_script = None
        for ext in [".sh", ".pl", ".py"]:
            potential_script = script_path / f"{script_file}{ext}"
            if potential_script.exists():
                found_script = potential_script.name
                break

        if found_script:
            next_execution_timestamp = convert_cron_to_timestamp(cron_expression)
            cron_jobs.append({
                "script_name": found_script,
                "cron_expression": cron_expression,
                "next_execution_timestamp": next_execution_timestamp
            })
            cron_description = get_description(cron_expression)
            print(f"  - {found_script}: {cron_expression} ({cron_description})")
        else:
            print(f"  - {script_name}: Unsupported script type or file not found")
    else:
        print(f"  - {script_name}: Invalid or missing cron expression")


### Determine the first script to run and print its next execution time
if cron_jobs:
    next_job = min(cron_jobs, key=lambda job: job["next_execution_timestamp"])
    next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_job["next_execution_timestamp"]).strftime("%A, %B %d, %Y %I:%M %p"))
    print(f"\n--> First execution will be {next_job['script_name']} on: {next_execution_readable}")

### Initialize next_execution_time
next_execution_time = min(job["next_execution_timestamp"] for job in cron_jobs)

### Endless loop
while True:
    current_time_timestamp = datetime.now().timestamp()

    for job in cron_jobs:
        script_name = job["script_name"]
        next_execution_timestamp = job["next_execution_timestamp"]

        if current_time_timestamp >= next_execution_timestamp:
            ### Execute script
            run_script(script_name)

            ### Plan next execution
            job["next_execution_timestamp"] = convert_cron_to_timestamp(job["cron_expression"])

            ### Print next execution time
            next_times = [job["next_execution_timestamp"] for job in cron_jobs]
            next_execution_time = min(next_times)
            next_execution_readable = convert_to_current_tz(datetime.fromtimestamp(next_execution_time)).strftime("%A, %B %d, %Y %I:%M %p")
            next_job = next((j for j in cron_jobs if j["next_execution_timestamp"] == next_execution_time), None)
            if next_job:
                print(f"\n\n--> Next execution will be {next_job['script_name']} on: {next_execution_readable}")

    ### Sleep until the next scheduled execution
    sleep_duration = next_execution_time - current_time_timestamp
    sleep(max(0, sleep_duration))  # Avoid negative sleep duration