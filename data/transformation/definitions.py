import os
from pathlib import Path

import dagster as dg

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets
from project import transformation_project


# would be BUILT dbt project
@dbt_assets(manifest=Path("packaged_dbt_project", "target", "manifest.json"))
def transformation_dbt_assets(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build", "--no-partial-parse"], context=context).stream()


@dg.asset(deps=["new_tenders"])
def example_asset(context: dg.AssetExecutionContext):
    context.log.info("test")


defs = dg.Definitions(
    assets=[example_asset, transformation_dbt_assets],
    resources={
        "dbt": DbtCliResource(project_dir=transformation_project),
    },
)
