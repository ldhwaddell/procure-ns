# --- Stage 1: Build -----------------------------------------------------
FROM python:3.10-slim AS builder

ARG DWH_POSTGRES_USER
ARG DWH_POSTGRES_PASSWORD
ARG DWH_POSTGRES_DB

ENV DWH_POSTGRES_USER=$DWH_POSTGRES_USER
ENV DWH_POSTGRES_PASSWORD=$DWH_POSTGRES_PASSWORD
ENV DWH_POSTGRES_DB=$DWH_POSTGRES_DB


WORKDIR /build

RUN pip install \
	dagster \
	dagster-dbt \
	dbt-postgres

COPY ./project.py .
COPY ./dbt_transform/ ./dbt_transform/

RUN dagster-dbt project prepare-and-package --file project.py

# --- Stage 2: Runtime -----------------------------------------------------

FROM python:3.10-slim

RUN pip install \
	dagster \
	dagster-dbt \
	dagster-postgres \
	dbt-postgres


WORKDIR /opt/dagster/app

COPY ./definitions.py .
COPY ./project.py .

COPY --from=builder /build/packaged_dbt_project/ packaged_dbt_project/

# Run dagster gRPC server on port 4000
EXPOSE 4000

CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4010", "-m", "definitions"]
