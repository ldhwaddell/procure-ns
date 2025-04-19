import asyncio
import json
from datetime import datetime

import dagster as dg
from dagster_docker import PipesDockerClient
from sqlalchemy import insert, select
from sqlalchemy.sql import text

from ingestion.models import MasterTender, NewTender
from ingestion.resources import DataWarehouseResource, ProxyResource
from ingestion.utils import (
    AuthRotator,
    ProxyRotator,
    scrape_tender,
    send_authenticated_request,
)


@dg.asset(compute_kind="docker", group_name="ingestion")
def new_tenders(
    context: dg.AssetExecutionContext,
    proxy: ProxyResource,
    dwh: DataWarehouseResource,
    docker_pipes_client: PipesDockerClient,
) -> dg.MaterializeResult:
    max_records = 16000
    proxy_conf = proxy.get_proxy_conf()
    # Runs the custom image and returns auth results
    (auth,) = docker_pipes_client.run(
        image="auth-scraper",
        command=["python", "main.py"],
        env={"PROXY_CONF": json.dumps(proxy_conf)},
        context=context,
    ).get_custom_messages()

    tenders_json = send_authenticated_request(auth, max_records)

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
            "new_records_ingested": dg.MetadataValue.int(len(new_rows)),
        }
    )


@dg.asset(compute_kind="docker", group_name="ingestion", deps=[new_tenders])
async def tender_metadata(
    context: dg.AssetExecutionContext,
    proxy: ProxyResource,
    dwh: DataWarehouseResource,
    docker_pipes_client: PipesDockerClient,
) -> dg.MaterializeResult:
    parallel_sessions_limit = 10
    proxy_conf = proxy.get_proxy_conf()

    async def get_auth():
        (auth,) = docker_pipes_client.run(
            image="auth-scraper",
            command=["python", "main.py"],
            env={"PROXY_CONF": json.dumps(proxy_conf)},
            context=context,
        ).get_custom_messages()
        return auth

    # Step 1: Get all new tenders
    sync_session = dwh.get_session()
    with sync_session() as session:
        new_tenders = session.execute(select(NewTender)).scalars().all()

    # Step 2: Process tenders asynchronously
    async_session = dwh.get_async_session()

    semaphore = asyncio.Semaphore(parallel_sessions_limit)
    proxy_rotator = ProxyRotator(50, proxy.get_proxy_conf)
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


@dg.asset(compute_kind="docker", group_name="ingestion")
def docker_test(
    context: dg.AssetExecutionContext,
    proxy: ProxyResource,
    docker_pipes_client: PipesDockerClient,
) -> dg.MaterializeResult:
    proxy_conf = proxy.get_proxy_conf()
    (results,) = docker_pipes_client.run(
        image="auth-scraper",
        command=["python", "main.py"],
        env={"PROXY_CONF": json.dumps(proxy_conf)},
        context=context,
    ).get_custom_messages()

    context.log.info(f"{type(results)}")
    context.log.info(f"%%%%%%%%%{results}%%%%%%%%%%%")

    return dg.MaterializeResult(
        metadata={
            "user_agent": "test",
        }
    )


defs = dg.Definitions(
    assets=[new_tenders, tender_metadata, docker_test],
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
        "docker_pipes_client": PipesDockerClient(),
    },
)
