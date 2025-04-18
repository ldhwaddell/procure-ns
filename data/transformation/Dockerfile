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

# package the dagster prokect into a dir
# then here we can copy in the whole dbt proj + just project.py
# now running prepare and packagine will build built_dbt_project
# COPY . .
COPY ./project.py .
COPY ./dbt_transform/ ./dbt_transform/

RUN dagster-dbt project prepare-and-package --file project.py

CMD ["bash"]

# --- Stage 2: Runtime -----------------------------------------------------

