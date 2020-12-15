FROM python:3.8-slim

# additional repositories for fonts
RUN echo "deb http://httpredir.debian.org/debian buster main contrib non-free" > /etc/apt/sources.list \
    && echo "deb http://httpredir.debian.org/debian buster-updates main contrib non-free" >> /etc/apt/sources.list \
    && echo "deb http://security.debian.org/ buster/updates main contrib non-free" >> /etc/apt/sources.list \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ttf-mscorefonts-installer \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR .

ENV PYTHONUNBUFFERED 1

COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir db

COPY . .

# give permission to execute start script
RUN chmod +x start.docker.sh

CMD ["./start.docker.sh"]
