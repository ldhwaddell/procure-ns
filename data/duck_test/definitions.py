from dagster_duckdb import DuckDBResource

from dagster import Definitions, asset, EnvVar


@asset
def iris_dataset(duckdb: DuckDBResource) -> None:
    with duckdb.get_connection() as conn:
        conn.execute("SELECT 'Hello, world'")


defs = Definitions(
    assets=[iris_dataset],
    resources={
        "duckdb": DuckDBResource(
            database=EnvVar("DWH_DUCKDB"),
        )
    },
)
