import dagster as dg
from tenders.resources import DataWarehouseResource, ProxyResource
from sqlalchemy.sql import text
from sqlalchemy import insert
from tenders.utils import launch_browser_and_get_auth, send_authenticated_request
from tenders.models import NewTender
import datetime
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


@dg.asset(compute_kind="docker", group_name="ingestion")
def new_tenders(
    proxy: ProxyResource, dwh: DataWarehouseResource
) -> dg.MaterializeResult:
    proxy_conf = proxy.get_proxy_conf()
    auth = launch_browser_and_get_auth(proxy_conf)
    tenders_json = send_authenticated_request(auth)

    tenders = tenders_json.get("tenderDataList", [])

    rows = [
        {
            "id": t["id"],
            "tenderId": t["tenderId"],
            "title": t.get("title"),
            "solicitationType": t.get("solicitationType"),
            "procurementEntity": t.get("procurementEntity"),
            "endUserEntity": t.get("endUserEntity"),
            "closingDate": datetime.fromisoformat(t["closingDate"])
            if t.get("closingDate")
            else None,
            "postDate": datetime.fromisoformat(t["postDate"]).date()
            if t.get("postDate")
            else None,
            "tenderStatus": t.get("tenderStatus"),
        }
        for t in tenders
    ]

    ddl = """
        DROP TABLE IF EXISTS new_tenders;

        CREATE TABLE new_tenders (
            "id" INTEGER PRIMARY KEY,
            "tenderId" TEXT,
            "title" TEXT,
            "solicitationType" TEXT,
            "procurementEntity" TEXT,
            "endUserEntity" TEXT,
            "closingDate" TIMESTAMP,
            "postDate" DATE,
            "tenderStatus" TEXT
        )
    """

    Session = dwh.get_session()
    with Session() as session:
        session.execute(text(ddl))
        if rows:
            session.execute(insert(NewTender), rows)
        session.commit()
    return dg.MaterializeResult(
        metadata={
            "records_ingested": dg.MetadataValue.int(len(rows)),
            "token": dg.MetadataValue.text(auth["jwt"]),
        }
    )


# dwh_job = dg.define_asset_job(
#     name="dwh_job", selection=["test_dwh"], executor_def=docker_executor
# )
#
# dwh_job_2 = dg.define_asset_job(name="dwh_job_2", selection=["test_dwh"])
#

defs = dg.Definitions(
    assets=[test_dwh, test_dwh_insert, new_tenders],
    # jobs=[dwh_job, dwh_job_2],
    resources={
        "dwh": DataWarehouseResource(
            username=dg.EnvVar("DWH_POSTGRES_USER"),
            password=dg.EnvVar("DWH_POSTGRES_PASSWORD"),
            db=dg.EnvVar("DWH_POSTGRES_DB"),
        ),
        "proxy": ProxyResource(
            username=dg.EnvVar("PROXY_USER"),
            password=dg.EnvVar("PROXY_PASSWORD"),
        ),
    },
)
