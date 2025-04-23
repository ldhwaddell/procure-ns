import asyncio
import fsspec
import json

import dagster as dg
import pandas as pd
from dagster_docker import PipesDockerClient
from dagster_duckdb import DuckDBResource

from ingestion.resources import ProxyResource
from ingestion.utils import (
    AuthRotator,
    ProxyRotator,
    scrape_tender,
    send_authenticated_request,
    table_exists,
)


@dg.asset(compute_kind="docker", group_name="ingestion")
def new_tenders(
    context: dg.AssetExecutionContext,
    proxy: ProxyResource,
    duckdb: DuckDBResource,
    docker_pipes_client: PipesDockerClient,
) -> dg.MaterializeResult:
    max_records = 1000
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
        if table_exists(conn, "raw_tenders"):
            conn.execute("""
                CREATE OR REPLACE TABLE new_tenders AS 
                SELECT df.*
                FROM df
                LEFT JOIN raw_tenders rt ON df.id = rt.id
                WHERE rt.id IS NULL
            """)
        else:
            conn.execute("""
                CREATE OR REPLACE TABLE new_tenders AS 
                SELECT * FROM df
            """)

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
        new_tenders = conn.execute("SELECT * FROM new_tenders").fetchdf()

    semaphore = asyncio.Semaphore(parallel_sessions_limit)
    proxy_rotator = ProxyRotator(50, proxy.get_proxy_conf)
    auth_rotator = AuthRotator(100, get_auth)
    timeout = 30

    tasks = [
        scrape_tender(tender_id, proxy_rotator, auth_rotator, timeout, semaphore)
        for tender_id in new_tenders["tenderId"]
    ]

    # 2D array: [[metadata], [metadata], None, ...]
    tender_metadata = await asyncio.gather(*tasks)

    # Flatten and remove empties
    tender_metadata = [
        item
        for tender_list in tender_metadata
        if tender_list is not None
        for item in tender_list
    ]

    # In-memory file system wizardry
    memfs = fsspec.filesystem("memory")
    with duckdb.get_connection() as conn:
        with memfs.open("tender_metadata.json", "w") as file:
            file.write(json.dumps(tender_metadata))
            context.log.info("Metadata dumped to memfs")

            # Register the memory filesystem and create the table
            conn.register_filesystem(memfs)

            if table_exists(conn, "raw_tenders"):
                conn.execute(
                    "INSERT INTO raw_tenders SELECT * FROM read_json_auto('memory://tender_metadata.json')"
                )
                context.log.info("Tenders inserted")
            else:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS raw_tenders AS SELECT * FROM read_json_auto('memory://tender_metadata.json')"
                )
                context.log.info("'raw_tenders' table created")

        preview_query = "SELECT * FROM RAW_TENDERS limit 10"
        preview_df = conn.execute(preview_query).fetchdf()

        row_count = conn.execute("SELECT COUNT(*) FROM raw_tenders").fetchone()
        count = row_count[0] if row_count else 0

    return dg.MaterializeResult(
        metadata={
            "raw_tenders_row_count": dg.MetadataValue.int(count),
            "raw_tenders_preview": dg.MetadataValue.md(
                preview_df.to_markdown(index=False)
            ),
        }
    )


defs = dg.Definitions(
    assets=[new_tenders, tender_metadata],
    resources={
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
