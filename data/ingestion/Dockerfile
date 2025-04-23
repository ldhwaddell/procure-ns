FROM python:3.10-slim

RUN pip install \
	dagster \
	dagster-postgres \
	dagster-docker \
	dagster-duckdb \
	dagster-duckdb-pandas \
	playwright \
	fake-useragent \
	httpx

WORKDIR /opt/dagster/app
COPY . /opt/dagster/app/ingestion

# Run dagster gRPC server on port 4000

EXPOSE 4000

# CMD allows this to be overridden from run launchers or executors that want
# to run other commands against your repository
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", "-m", "ingestion.definitions"]
