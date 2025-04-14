import dagster as dg
from tenders.resources import DataWarehouseResource, ProxyResource
from sqlalchemy.sql import text
from sqlalchemy import insert
from tenders.utils import launch_browser_and_get_auth, send_authenticated_request
from tenders.models import NewTender
from datetime import datetime


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
    assets=[new_tenders],
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
