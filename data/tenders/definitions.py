import dagster as dg
from tenders.resources import DataWarehouseResource
from sqlalchemy.sql import text
# from dagster_docker import docker_executor


@dg.asset(compute_kind="dwh", group_name="ingestion")
def test_dwh(dwh: DataWarehouseResource) -> dg.MaterializeResult:
    Session = dwh.get_session()
    with Session() as session:
        result = session.execute(
            text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        )

        tables = result.fetchall()
        table_names = [row[0] for row in tables]
        print("Tables in public schema:", table_names)

    return dg.MaterializeResult(
        metadata={
            "table_count": dg.MetadataValue.int(len(tables)),
            "test": dg.MetadataValue.md("md test"),
        }
    )

    # with dwh.connect() as conn:
    #     with conn.cursor() as cursor:
    #         # Built-in query to list tables in the current schema (should return empty if no user tables exist)
    #         cursor.execute("""
    #             SELECT table_name
    #             FROM information_schema.tables
    #             WHERE table_schema = 'public';
    #         """)
    #
    #         tables = cursor.fetchall()
    #         print("Tables in public schema:", tables)
    #
    # return dg.MaterializeResult(
    #     metadata={
    #         "table_count": dg.MetadataValue.int(len(tables)),
    #         "test": dg.MetadataValue.md("md test"),
    #     }
    # )


# dwh_job = dg.define_asset_job(
#     name="dwh_job", selection=["test_dwh"], executor_def=docker_executor
# )
#
# dwh_job_2 = dg.define_asset_job(name="dwh_job_2", selection=["test_dwh"])
#

defs = dg.Definitions(
    assets=[test_dwh],
    # jobs=[dwh_job, dwh_job_2],
    resources={
        "dwh": DataWarehouseResource(
            username=dg.EnvVar("DWH_POSTGRES_USER"),
            password=dg.EnvVar("DWH_POSTGRES_PASSWORD"),
            db=dg.EnvVar("DWH_POSTGRES_DB"),
        )
    },
)
