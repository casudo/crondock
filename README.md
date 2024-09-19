# Crondock
Crondock is a solution to run cron jobs in Docker containers. It's a simple Python script that runs your scripts on the specified cron schedule.

---

##### Table of Contents
- [Docker](#docker)
  - [Docker Run](#docker-run)
  - [Docker Compose](#docker-compose)
- [Planned for the future](#planned-for-the-future)

--- 

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