FROM python:3.12.0-slim

### Set working directory and copy files
WORKDIR /code
COPY . /code

### Install dependencies (trusted-host due to SSL error: https://stackoverflow.com/a/29751768)
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

### Set entrypoint
### https://stackoverflow.com/a/29745541
ENTRYPOINT ["python", "-u", "/code/entrypoint.py"]