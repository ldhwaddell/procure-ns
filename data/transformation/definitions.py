from pathlib import Path

import dagster as dg

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets, get_asset_key_for_model

transformation_project = DbtProject(
    project_dir=Path(__file__).joinpath("..", "dbt").resolve(),
    packaged_project_dir=Path(__file__).joinpath("..", "dbt-project").resolve(),
)
transformation_project.prepare_if_dev()


@dbt_assets(manifest=transformation_project.manifest_path)
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
    resources=(
        {
            "dbt": DbtCliResource(project_dir=transformation_project),
        },
    ),
)
