# Crondock
Crondock is a solution to run cron jobs in Docker containers. It's a simple Python script that runs your scripts on the specified cron schedule.

---

##### Table of Contents
- [Docker](#docker)
  - [Docker Run](#docker-run)
  - [Docker Compose](#docker-compose)
- [Planned for the future](#planned-for-the-future)

## Docker
Before starting the container, you'll need to set some mandatory environment variables:  

| Variable | Required | Description |
| --- | --- | --- |
| `RS_<x>` | No | The cron expression when the script should run (e.g. `0 11 1,15 * *`). `<x>` is the name of your script (without the extension!). |

You can add as many scripts as you want, just follow the above format.

> [!NOTE]
Make sure that those scripts are mounted properly in the container!

### Docker Run
```bash
docker run -d \  
    --name crondock \ 
    --restart unless-stopped \
    -v /path/to/your/scripts:/code \
    -e RS_TESTSCRIPT="*/1 * * * *" \
    -e RS_OTHERSCRIPT="*/5 * * * *" \
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
      - /path/to/your/scripts:/code
    environment:
        - RS_TESTSCRIPT="*/1 * * * *"
        - RS_OTHERSCRIPT="*/5 * * * *"
```

Save the above as `docker-compose.yml` and run it with `docker-compose up -d`.  

## Planned for the future
- Better logging
- Better error handling
- (Instead of cron expression, use smth like "Every 5 minutes" or "Every 1 hour")
- Fix TZ in logs to CEST