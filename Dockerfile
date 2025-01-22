FROM ubuntu:25.04
RUN apt-get update && apt-get install -y rustc python3 python3-pip

WORKDIR /app
# Only copy the requirements file first, so that we can cache the installation of the requirements
COPY ./app/requirements.txt /app/requirements.txt
# --break-system-package sounds bad, but not really that bad.
RUN pip3 install -r requirements.txt --break-system-package
COPY ./app /app

# Our Bucket Secret (Build will break without this, which is good as it is necessary for proper operation)
COPY ./google_secrets.json /
ENV GOOGLE_APPLICATION_CREDENTIALS=/google_secrets.json

ENTRYPOINT [ "python3", "main.py" ]