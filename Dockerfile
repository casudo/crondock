FROM python:3.12.0

### Set working directory and copy files
RUN mkdir /code
WORKDIR /code
ADD . /code/
### TODO: Copy?

### Make all scripts executable
RUN chmod 770 /code/*

### Install dependencies (trusted-host due to SSL error: https://stackoverflow.com/a/29751768)
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

### Set entrypoint
### https://stackoverflow.com/a/29745541
ENTRYPOINT ["python", "-u", "/code/entrypoint.py"]