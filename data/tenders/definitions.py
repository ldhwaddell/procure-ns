import dagster as dg
from tenders.resources import DataWarehouseResource, ProxyResource
from sqlalchemy.sql import text
from sqlalchemy import insert, select
from tenders.utils import launch_browser_and_get_auth, send_authenticated_request
from tenders.models import NewTender, MasterTender, TenderMetadata
from datetime import datetime


@dg.asset(compute_kind="docker", group_name="ingestion")
def new_tenders(
    proxy: ProxyResource, dwh: DataWarehouseResource
) -> dg.MaterializeResult:
    proxy_conf = proxy.get_proxy_conf()
    auth = launch_browser_and_get_auth(proxy_conf)
    tenders_json = send_authenticated_request(auth)

    tenders = tenders_json.get("tenderDataList", [])

    incoming_rows = [
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

        existing_ids = {
            row[0] for row in session.execute(select(MasterTender.id)).all()
        }

        # Filter rows that are not in MasterTender
        new_rows = [row for row in incoming_rows if row["id"] not in existing_ids]

        if new_rows:
            session.execute(insert(NewTender), new_rows)
        session.commit()
    return dg.MaterializeResult(
        metadata={
            "records_ingested": dg.MetadataValue.int(len(new_rows)),
            "token": dg.MetadataValue.text(auth["jwt"]),
        }
    )


@dg.asset(compute_kind="docker", group_name="ingestion", deps=[new_tenders])
def tender_metadata(
    proxy: ProxyResource, dwh: DataWarehouseResource
) -> dg.MaterializeResult:
    Session = dwh.get_session()
    with Session() as session:
        new_tenders = session.execute(select(NewTender)).scalars().all()

        # proxy_conf = proxy.get_proxy_conf()
        # auth = launch_browser_and_get_auth(proxy_conf)

        # For each new tender:
        # pull the metadata
        # insert new tender into master tenders with metadata

        for tender in new_tenders:
            master = MasterTender(
                id=tender.id,
                tenderId=tender.tenderId,
                title=tender.title,
                solicitationType=tender.solicitationType,
                procurementEntity=tender.procurementEntity,
                endUserEntity=tender.endUserEntity,
                closingDate=tender.closingDate,
                postDate=tender.postDate,
                tenderStatus=tender.tenderStatus,
            )

            master.tenderMetadata = TenderMetadata(createdBy="Jerome")

            session.add(master)

        session.commit()

    return dg.MaterializeResult(
        metadata={
            "new_tenders": dg.MetadataValue.int(len(new_tenders)),
        }
    )


# dwh_job = dg.define_asset_job(
#     name="dwh_job", selection=["test_dwh"], executor_def=docker_executor
# )
#
# dwh_job_2 = dg.define_asset_job(name="dwh_job_2", selection=["test_dwh"])
#

defs = dg.Definitions(
    assets=[new_tenders, tender_metadata],
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
