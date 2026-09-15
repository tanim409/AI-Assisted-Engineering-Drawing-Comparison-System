# PostgreSQL migration

The application now uses PostgreSQL through `psycopg`, not MySQL or PyMySQL.

## Start the new database

1. Stop the old MySQL stack: `docker compose down`.
2. Start PostgreSQL and the application: `docker compose up --build`.
3. Set `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DATABASE` in `backend/.env` when running the backend outside Docker.

The application initializes its PostgreSQL schema at startup. The prior MySQL volume is untouched; it is not compatible with PostgreSQL and is not mounted by the new Compose stack.

## Existing data

This code migration does not copy existing MySQL rows. Export or migrate any data you need before deleting the old MySQL container or `mysql_data` volume. The old MySQL container can remain stopped as a backup until that is complete.
