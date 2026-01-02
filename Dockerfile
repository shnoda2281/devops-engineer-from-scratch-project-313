FROM python:3.14-alpine

RUN apk add --no-cache \
    build-base \
    curl \
    git \
    bash \
    make \
    nodejs \
    npm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project

ENV UV_PYTHON_DOWNLOADS=never
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --system --frozen

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .

EXPOSE 8080
CMD ["uv", "run", "--system", "fastapi", "run", "main:app", "--host", "0.0.0.0", "--port", "8080"]
