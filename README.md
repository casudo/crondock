# Crondock
Crondock is a solution to run cron jobs in Docker containers. It's a simple Python script that runs your scripts on the specified cron schedule.

---

##### Table of Contents
- [Key Features](#key-features)
- [Docker](#docker)
  - [Docker Run](#docker-run)
  - [Docker Compose](#docker-compose)
- [Planned for the future](#planned-for-the-future)

--- 

## Key Features
**Cron Job Scheduling**:
  - Automatically detects environment variables prefixed with `RS_` to set up cron job schedules for scripts.
  - Supports flexible cron expressions for scheduling (e.g., "*/5 * * * *").

**Multi-Script Execution**:
  - Supports the execution of multiple script types (`.sh`, `.py`, etc.) using an `EXTENSION_MAP` to associate the script extension with the proper interpreter.
  - Can be extended to support additional script types like Perl (`.pl`), Ruby (`.rb`), PHP (`.php`), etc.

**Parallel Execution**:
  - Uses `concurrent.futures.ThreadPoolExecutor` to run scheduled scripts in parallel without blocking the execution of other scheduled jobs.

**Graceful Shutdown Handling**:
  - Listens for `SIGTERM` and `SIGINT` signals (e.g., from Docker stop or Ctrl+C) and ensures that the container shuts down gracefully.

**Timezone Support**:
  - Converts all timestamps to the specified timezone (defaults to `Europe/Berlin` but can be customized using the `TZ` environment variable).

**Script Validation**:
  - Validates the existence of scripts in `/code/scripts/` before execution and ensures they have the correct file extension.
  - Logs whether the scripts are present and whether the cron expressions are valid before proceeding with execution.

**Automatic Logging**:
  - Provides informative logs about script execution, including success/failure messages, cron expression schedules, and detailed timestamps for each job.

**Customizable Scheduling**:
  - Detects scripts with underscore-separated folder structures, allowing for organized subfolder script execution (e.g., `folder_script.sh` runs `folder/script.sh`).
   
**Lightweight and Extensible**:
  - Designed to be easily extensible with more interpreters or custom scheduling logic.
  - Lightweight and fast execution, optimized for running in a Docker container.


## Docker
Before starting the container, you'll need to set some mandatory environment variables:  

| Variable | Required | Description |
| --- | --- | --- |
| `RS_<x>` | No | The cron expression when the script should run (e.g. `0 11 1,15 * *`). `<x>` is the name of your script (without the extension!). |
| `TZ` | No | Specify the timezone for the container. Default is `Europe/Berlin`. |

You can add as many scripts as you want, just follow the above format.

> [!IMPORTANT]
Make sure that those scripts are mounted properly in the container AND that they are executable!

### Docker Run
```bash
docker run -d \  
    --name crondock \ 
    --restart unless-stopped \
    -v /path/to/your/scripts:/code/scripts \
    -e RS_TESTSCRIPT="*/1 * * * *" \
    -e RS_OTHERSCRIPT="*/5 * * * *" \
    -e TZ=Europe/Berlin \
    ghcr.io/casudo/crondock:latest
```

### Docker Compose
```yml
version: "3.8"

services:
  crondock:
    container_name: crondock
    image: ghcr.io/casudo/grei:latest
    restart: unless-stopped
    volumes:
      - /path/to/your/scripts:/code/scripts
    environment:
        - RS_TESTSCRIPT="*/1 * * * *"
        - RS_OTHERSCRIPT="*/5 * * * *"
        - TZ=Europe/Berlin
```

Save the above as `docker-compose.yml` and run it with `docker-compose up -d`.  

## Planned for the future
- Better error handling
- Guide on how to mount scripts and subfolders
- (Instead of cron expression, use smth like "Every 5 minutes" or "Every 1 hour")
- Ability to run commands instead of scripts
- Ensure that scripts are executable
