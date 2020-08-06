FROM python:3.8-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

WORKDIR .

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir db

COPY . .

CMD ["git", "pull"]
CMD ["python", "-u", "HatBot.py"]
