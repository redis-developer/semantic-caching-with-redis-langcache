This is a [Redis](https://redis.io/) semantic caching demo for Python using:

- [Redis Cloud](https://redis.io/try-free/)
- [FastAPI](https://fastapi.tiangolo.com/)

## Requirements

- [make](https://www.make.com/en)
- [python>=3.10](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/)
- [docker](https://www.docker.com/)
  - Optional outside tests

## Getting started

Copy and edit the `.env` file:

```bash
cp .env.example .env
```

Your `.env` file should contain the connection string you copied from Redis Cloud.

Available settings:

- `APP_ENV=development|test|production`
- `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL`
- `LOG_STREAM_KEY=logs`
- `PORT=8080`
- `REDIS_URL=redis://...`
- `LANGCACHE_TTL_SECONDS=3600`
- `LANGCACHE_CACHE_THRESHOLD=0.65`
- `LANGCACHE_KNOWLEDGE_THRESHOLD=0.35`

For docker, `.env.docker` should use container-internal addresses. Example:

```bash
APP_ENV=production
LOG_LEVEL=INFO
LOG_STREAM_KEY=logs
REDIS_URL="redis://redis:6379"
```

Next, spin up docker containers:

```bash
make docker
```

You should have a server running on `http://localhost:<port>` where the port is set in your `.env` file (default is 8080). You can test the following routes:

1. `POST /api/langcache/ask` - Ask the semantic cache a support question with `{ "question": "How do I reset my password?" }`
2. `GET /api/langcache/stats` - Read request, hit, miss, and hit-rate metrics

The answer payload includes:

- `cacheHit`
- `matchedPrompt`
- `similarity`
- `cacheKey`
- `ttlSeconds`

## Logging

Requests and component logs are written to stdout. They are also shipped to Redis as stream entries via `XADD` on the key configured by `LOG_STREAM_KEY` (default `logs`).

## Running tests

The test suite lives in `__test__` and can be run with:

```bash
make test
```

If `REDIS_URL` points at the default local Redis and nothing is listening on it, the tests will start the `redis` service with docker compose automatically and stop it afterward.

## Running locally outside docker

Install dependencies and run the dev server:

```bash
make install
make dev
```

For a production-style server:

```bash
make serve
```

## Other scripts

Run `make` to see the list of available commands.

Useful targets:

- `make format`
- `make lint`
- `make update`
- `make lock`

## Connecting to Redis Cloud

If you don't yet have a database setup in Redis Cloud [get started here for free](https://redis.io/try-free/).

To connect to a Redis Cloud database, log into the console and find the following:

1. The `public endpoint`
2. Your `username`
3. Your `password`

Combine them into a connection string and put it in `.env` and `.env.docker`. Example:

```bash
REDIS_URL="redis://default:<password>@redis-#####.c###.us-west-2-#.ec2.redns.redis-cloud.com:#####"
```

Run `make test` to verify the connection.

## Learn more

- [Redis Documentation](https://redis.io/docs/latest/)
- [Learn Redis](https://redis.io/learn/)
- [Redis Demo Center](https://redis.io/demo-center/)
