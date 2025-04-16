FROM python:3.10-slim

# Checkout and install dagster libraries needed to run the gRPC server
# exposing your repository to dagster-webserver and dagster-daemon, and to load the DagsterInstance

RUN pip install \
	dagster \
	dagster-postgres \
	dagster-docker \
	dagster-dbt \
	dbt-postgres


# Add repository code

WORKDIR /opt/dagster/app
RUN mkdir data
COPY . /opt/dagster/app/transformation

ENV DBT_PROJECT_DIR=/opt/dagster/app/transformation/dbt_transform

WORKDIR ${DBT_PROJECT_DIR}
RUN dbt deps && dbt parse


RUN find target -type f -name 'manifest.json' -exec cp {} target/manifest.json \;
# Run dagster gRPC server on port 4000

EXPOSE 4000

# CMD allows this to be overridden from run launchers or executors that want
# to run other commands against your repository
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4010", "-m", "transformation.definitions"]
