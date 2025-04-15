import dagster as dg
from tenders.resources import DataWarehouseResource, ProxyResource
from sqlalchemy.sql import text
from sqlalchemy import insert, select
from tenders.utils import (
    scrape_tender,
    launch_browser_and_get_auth,
    send_authenticated_request,
    ProxyRotator,
    AuthRotator,
)
from tenders.models import NewTender, MasterTender
from datetime import datetime
import asyncio


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
async def tender_metadata(
    proxy: ProxyResource, dwh: DataWarehouseResource
) -> dg.MaterializeResult:
    parallel_sessions_limit = 10
    proxy_conf = proxy.get_proxy_conf()

    async def get_auth():
        return await asyncio.to_thread(launch_browser_and_get_auth, proxy_conf)

    # Step 1: Get all new tenders
    sync_session = dwh.get_session()
    with sync_session() as session:
        new_tenders = session.execute(select(NewTender)).scalars().all()

    # Step 2: Process tenders asynchronously
    async_session = dwh.get_async_session()

    semaphore = asyncio.Semaphore(parallel_sessions_limit)
    proxy_rotator = ProxyRotator(10, proxy.get_proxy_conf)
    auth_rotator = AuthRotator(100, get_auth)
    timeout = 30

    tasks = [
        scrape_tender(t, proxy_rotator, auth_rotator, async_session, timeout, semaphore)
        for t in new_tenders
    ]
    await asyncio.gather(*tasks)

    return dg.MaterializeResult(
        metadata={
            "new_tenders": dg.MetadataValue.int(len(new_tenders)),
            "tasks": dg.MetadataValue.int(len(tasks)),
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


# master = MasterTender(
#     id=tender.id,
#     tenderId=tender.tenderId,
#     title=tender.title,
#     solicitationType=tender.solicitationType,
#     procurementEntity=tender.procurementEntity,
#     endUserEntity=tender.endUserEntity,
#     closingDate=tender.closingDate,
#     postDate=tender.postDate,
#     tenderStatus=tender.tenderStatus,
#             )
#
#             master.tenderMetadata = TenderMetadata(createdBy="Jerome")
#
#             session.add(master)
#
#         session.commit()
#
