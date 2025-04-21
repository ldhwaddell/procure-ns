# data

This folder contain all required logic for the containerized deployment of the ingestion pipeline. Current deployment is on a Hetzner VPS

### Current Structure

```bash
.
├── .env <- Connection for DB, DWH, Proxies
├── .gitignore
├── .python-version
├── Dockerfile
├── README.md
├── alembic <- Enable easy sync of expected DB models in ingestion/models.py and DWH
│   ├── env.py
│   ├── script.py.mako
├── alembic.ini
├── dagster.yaml <- Configure the global dagster settings (env vars, storage, logging, scheduling, ...)
├── docker-compose.yaml <- Main container definitions
├── ingestion <- ingestion code location, builds into ingestion container
│   ├── Dockerfile
│   ├── __init__.py
│   ├── assets.py
│   ├── definitions.py
│   ├── models.py
│   ├── resources.py
│   └── utils.py
├── pyproject.toml <- Track UV dependencies for local dev
├── transformation <- transformation code location, builds into transformation container
│   ├── Dockerfile
│   ├── dbt_transform <- Starter DBT project + models
│   │   ├── .gitignore
│   │   ├── README.md
│   │   ├── analyses
│   │   │   └── .gitkeep
│   │   ├── dbt_project.yml
│   │   ├── logs
│   │   │   └── dbt.log
│   │   ├── macros
│   │   │   └── .gitkeep
│   │   ├── models
│   │   │   └── example
│   │   │       ├── my_first_dbt_model.sql
│   │   │       ├── my_second_dbt_model.sql
│   │   │       └── schema.yml
│   │   └── profiles.yml
│   ├── definitions.py
│   └── project.py
├── uv.lock
└── workspace.yaml <- Defines code locations for the ingestion and transformation containers
```

### TODO

1. Fix DBT paths in conatinerized deployment `[DONE]`
   - The current implementation does not correctly locate the target directory build by DBT. This leads to dag runs needing to re-build the `manifest.json` file as they are ran. This is messy, and will create a bottleneck as DBT project complexity grows.
1. Use the `dagster-docker` package `[DONE]`
   - Current implementation manually spawns docker containers to pull auth credentials. This should be built into a single container, and then ran from the dagster asset. Not only is this more cohesive, it will solve the weird async + websocket addressing workarounds that are currently required.
1. Run `tender_metadata` asset based on a sensor
   - It should not run if the `new_tenders` asset returns 0 (meaning no new awarded tenders)
1. Build out DBT models
1. Investigate switching to `duckdb` as data warehouse

### Notes

1. Can't use env vars in dagster.yaml like we can with docker compose. See [issue](https://github.com/dagster-io/dagster/issues/18729)
