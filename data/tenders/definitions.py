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


@dg.asset(compute_kind="dwh", group_name="ingestion")
def test_dwh_insert(dwh: DataWarehouseResource) -> dg.MaterializeResult:
    Session = dwh.get_session()

    with Session() as session:
        # Create table (if not exists)
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_data (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            );
        """)
        )

        # Insert test rows
        session.execute(
            text("""
            INSERT INTO test_data (name, value) VALUES
            ('alpha', 10),
            ('beta', 20),
            ('gamma', 30)
            ON CONFLICT DO NOTHING;
        """)
        )

        # Preview rows
        result = session.execute(text("SELECT * FROM test_data LIMIT 10;"))
        column_names = result.keys()
        count_result = session.execute(text("SELECT COUNT(*) FROM test_data;"))
        row_count = count_result.scalar_one()

    return dg.MaterializeResult(
        metadata={
            "row_count": dg.MetadataValue.int(row_count),
            "columns": dg.MetadataValue.json(list(column_names)),
        }
    )


# dwh_job = dg.define_asset_job(
#     name="dwh_job", selection=["test_dwh"], executor_def=docker_executor
# )
#
# dwh_job_2 = dg.define_asset_job(name="dwh_job_2", selection=["test_dwh"])
#

defs = dg.Definitions(
    assets=[test_dwh, test_dwh_insert],
    # jobs=[dwh_job, dwh_job_2],
    resources={
        "dwh": DataWarehouseResource(
            username=dg.EnvVar("DWH_POSTGRES_USER"),
            password=dg.EnvVar("DWH_POSTGRES_PASSWORD"),
            db=dg.EnvVar("DWH_POSTGRES_DB"),
        )
    },
)
