import dagster as dg
from tenders.resources import DataWarehouseResource


@dg.asset(
    op_tags={"operation": "example"},
    partitions_def=dg.DailyPartitionsDefinition("2024-01-01"),
)
def example_asset(context: dg.AssetExecutionContext):
    context.log.info(context.partition_key)


partitioned_asset_job = dg.define_asset_job(
    "partitioned_job", selection=[example_asset]
)


@dg.asset(compute_kind="dwh", group_name="ingestion")
def test_dwh(dwh: DataWarehouseResource) -> None:
    with dwh.connect() as conn:
        with conn.cursor() as cursor:
            # Built-in query to list tables in the current schema (should return empty if no user tables exist)
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """)

            tables = cursor.fetchall()
            print("Tables in public schema:", tables)


defs = dg.Definitions(
    assets=[example_asset],
    jobs=[partitioned_asset_job],
    resources={
        "dwh": DataWarehouseResource(
            username=dg.EnvVar("DWH_POSTGRES_USER"),
            password=dg.EnvVar("DWH_POSTGRES_PASSWORD"),
            db=dg.EnvVar("DWH_POSTGRES_DB"),
        )
    },
)
