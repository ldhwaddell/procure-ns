import asyncio
import json

import dagster as dg
import pandas as pd
from dagster_docker import PipesDockerClient
from dagster_duckdb import DuckDBResource
from sqlalchemy import select

from ingestion.models import NewTender
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
    duckdb: DuckDBResource,
    docker_pipes_client: PipesDockerClient,
) -> dg.MaterializeResult:
    max_records = 50
    proxy_conf = proxy.get_proxy_conf()

    # Runs the custom image and returns auth results
    # the first item in the response sequence is guaranteed to be the auth data,
    # unless an error ocurred in which case the asset would already have failed

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
        }
        for t in tenders
    ]

    df = pd.DataFrame(incoming_rows)

    # Create the new table of unscraped tenders based on those that have not been inserted into the raw_tenders table yet
    with duckdb.get_connection() as conn:
        conn.execute(
            """
            CREATE OR REPLACE TABLE new_tenders AS 
            SELECT df.*
            FROM df
            LEFT JOIN raw_tenders rt ON df.id = rt.id
            WHERE rt.id IS NULL
            """
        )

        preview_query = "select * from new_tenders limit 10"
        preview_df = conn.execute(preview_query).fetchdf()

        row_count = conn.execute("select count(*) from new_tenders").fetchone()
        count = row_count[0] if row_count else 0

    return dg.MaterializeResult(
        metadata={
            "new_tenders_row_count": dg.MetadataValue.int(count),
            "new_tenders_preview": dg.MetadataValue.md(
                preview_df.to_markdown(index=False)
            ),
        }
    )


@dg.asset(compute_kind="docker", group_name="ingestion", deps=[new_tenders])
async def tender_metadata(
    context: dg.AssetExecutionContext,
    proxy: ProxyResource,
    duckdb: DuckDBResource,
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

    with duckdb.get_connection() as conn:
        new_tenders = conn.execute("select * from new_tenders").fetchdf()

    semaphore = asyncio.Semaphore(parallel_sessions_limit)
    proxy_rotator = ProxyRotator(50, proxy.get_proxy_conf)
    auth_rotator = AuthRotator(100, get_auth)
    timeout = 30

    tasks = [
        scrape_tender(tender_id, proxy_rotator, auth_rotator, timeout, semaphore)
        for tender_id in new_tenders["tenderId"]
    ]

    tender_metadata = await asyncio.gather(*tasks)

    # Flatten and remove empties
    tender_metadata_df = pd.DataFrame(
        [
            item
            for tender_list in tender_metadata
            if tender_list is not None
            for item in tender_list
        ]
    )

    with duckdb.get_connection() as conn:
        conn.execute("insert into raw_tenders select * from tender_metadata_df")

        preview_query = "select * from raw_tenders limit 10"
        preview_df = conn.execute(preview_query).fetchdf()

        row_count = conn.execute("select count(*) from raw_tenders").fetchone()
        count = row_count[0] if row_count else 0

    return dg.MaterializeResult(
        metadata={
            "raw_tenders_row_count": dg.MetadataValue.int(count),
            "raw_tenders_preview": dg.MetadataValue.md(
                preview_df.to_markdown(index=False)
            ),
        }
    )

    # # Step 1: Get all new tenders
    # sync_session = dwh.get_session()
    # with sync_session() as session:
    #     new_tenders = session.execute(select(NewTender)).scalars().all()
    #
    # # Step 2: Process tenders asynchronously
    # async_session = dwh.get_async_session()
    #
    #
    # tasks = [
    #     scrape_tender(t, proxy_rotator, auth_rotator, async_session, timeout, semaphore)
    #     for t in new_tenders
    # ]
    # await asyncio.gather(*tasks)
    #
    # return dg.MaterializeResult(
    #     metadata={
    #         "new_tenders": dg.MetadataValue.int(len(new_tenders)),
    #         "tasks": dg.MetadataValue.int(len(tasks)),
    #     }
    # )
    #


defs = dg.Definitions(
    assets=[new_tenders, tender_metadata],
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
        "duckdb": DuckDBResource(
            database=dg.EnvVar("DWH_DUCKDB"),
        ),
    },
)
