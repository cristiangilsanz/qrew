# Docker

Run the entire stack in containers with a single command. No local language runtimes required.


## Start everything

```bash
docker compose up
```

This builds all service images and starts them along with PostgreSQL, Redis, and NATS. Watch the logs until all healthchecks pass.

To run in the background:

```bash
docker compose up -d
```

Follow logs afterwards:

```bash
docker compose logs -f
```


## Seed the database

Once services are healthy, load demo data:

```bash
just db-seed
```

This is idempotent. Safe to run multiple times.


## Access points

| URL | Service |
|---|---|
| `http://localhost:3000` | Frontend app |
| `http://localhost:8000` | API gateway |
| `http://localhost:5432` | PostgreSQL |
| `http://localhost:6379` | Redis |
| `http://localhost:4222` | NATS |


## Rebuild after code changes

Services do not hot-reload in Docker mode. Rebuild after making changes:

```bash
docker compose up --build
```

To rebuild a single service:

```bash
docker compose up --build identity
```


## Tear down

Stop all containers but preserve data volumes:

```bash
docker compose stop
```

Resume later:

```bash
docker compose start
```

Full teardown. Removes containers, images, and all data:

```bash
just shutdown
```


## Logs for a specific service

```bash
docker compose logs -f identity
docker compose logs -f gateway
docker compose logs -f app
```


## Running only infrastructure

If you want to run application code locally but use Docker for PostgreSQL, Redis, and NATS:

```bash
docker compose up postgres redis nats -d --wait
```

Then follow the [LOCAL-DEVELOPMENT.md](LOCAL-DEVELOPMENT.md) guide.


## Configuring services for Docker

In Docker mode each service reads from `config/local.yaml`. The `docker-compose.yml` mounts these files at container startup. If a `local.yaml` does not exist, the service will use defaults defined in `config/default.yaml`. This is fine for infrastructure settings but third-party keys such as Stripe must be filled in manually before the relevant service will work.

Copy the examples once:

```bash
for svc in identity catalog sales ticketing payments entry audit; do
  cp apps/api/services/$svc/config/local.yaml.example apps/api/services/$svc/config/local.yaml
done
cp apps/api/gateway/config/local.yaml.example apps/api/gateway/config/local.yaml
```

**Never commit `local.yaml` files.** They are gitignored.
