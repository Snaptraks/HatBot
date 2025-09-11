FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y wget

# additional repositories for fonts
RUN wget https://gist.githubusercontent.com/hakerdefo/5e1f51fa93ff37871b9ff738b05ba30f/raw/7b5a0ff76b7f963c52f2b33baa20d8c4033bce4d/sources.list -O /etc/apt/sources.list
# RUN sed -i'.bak' 's/$/ contrib/' /etc/apt/sources.list

RUN apt-get update \
    && apt-get install -y --no-install-recommends git sqlite3 ttf-mscorefonts-installer \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot
RUN mkdir /bot/db

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /bot
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/bot/.venv/bin:$PATH"

CMD ["uv", "run", "HatBot.py"]
