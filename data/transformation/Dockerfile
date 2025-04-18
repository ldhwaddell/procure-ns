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

COPY ./dbt_dagster/project.py .
COPY ./dbt_transform/ ./dbt_transform/

RUN dagster-dbt project prepare-and-package --file project.py

# --- Stage 2: Runtime -----------------------------------------------------

# FROM python:3.10-slim
#
# # Add repository code
#
# RUN pip install \
# 	dagster \
# 	dagster-dbt \
# 	dagster-postgres \
# 	dbt-postgres
#
#
# WORKDIR /opt/dagster/app
#
# # now we need to copy in the BUILT dbt project and the whole dagster project. righ???
#
# # i dont know if my need config files from the raw dbt project?
#
# # might not need parent transformation folder
# # base dir it copies into could just have 2 folders for dagster + dbt?
# COPY --from=builder /build/packaged_dbt_project/ /opt/dagster/app/
# COPY ./dagster_transform/ ./dagster_transform/
#
# # Run dagster gRPC server on port 4000
# EXPOSE 4000
#
# # CMD allows this to be overridden from run launchers or executors that want
# # to run other commands against your repository
# maybe change to dagster_transform.definitions
# CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4010", "-m", "transformation.definitions"]
