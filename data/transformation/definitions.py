import os
from pathlib import Path

import dagster as dg

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets
from transformation.project import transformation_project


# would be BUILT dbt project
@dbt_assets(manifest=Path("transformation", "packaged_dbt_project", "target", "manifest.json"))
def transformation_dbt_assets(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


@dg.asset(
    op_tags={"operation": "example"},
    partitions_def=dg.DailyPartitionsDefinition("2024-01-01"),
)
def example_asset(context: dg.AssetExecutionContext):
    context.log.info(context.partition_key)


defs = dg.Definitions(
    assets=[example_asset, transformation_dbt_assets],
    resources={
        "dbt": DbtCliResource(project_dir=transformation_project),
    },
)
