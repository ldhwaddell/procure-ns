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

COPY . .

RUN dagster-dbt project prepare-and-package --file project.py

CMD ["bash"]

# --- Stage 2: Runtime -----------------------------------------------------

# FROM python:3.10-slim
#
# # Add repository code
#
# RUN pip install \
# 	dagster \
# 	dagster-dbt \
# 	dbt-postgres
#
#
# WORKDIR /opt/dagster/app
# # RUN mkdir data
#
# COPY --from=builder /build/transformation /opt/dagster/app/transformation
#
# # Run dagster gRPC server on port 4000
# EXPOSE 4000
#
# # CMD allows this to be overridden from run launchers or executors that want
# # to run other commands against your repository
# CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4010", "-m", "transformation.definitions"]
