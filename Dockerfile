FROM python:3.12-slim

RUN apt-get update && apt-get install -y wget

# additional repositories for fonts
RUN wget https://gist.githubusercontent.com/hakerdefo/5e1f51fa93ff37871b9ff738b05ba30f/raw/7b5a0ff76b7f963c52f2b33baa20d8c4033bce4d/sources.list -O /etc/apt/sources.list
# RUN sed -i'.bak' 's/$/ contrib/' /etc/apt/sources.list

RUN apt-get update \
    && apt-get install -y --no-install-recommends git sqlite3 ttf-mscorefonts-installer \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot

ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /bot/db

COPY . .

CMD ["python", "HatBot.py"]
