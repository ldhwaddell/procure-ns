import os
from pathlib import Path

import dagster as dg

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

transformation_project = DbtProject(
    project_dir=Path(__file__).joinpath("..", "dbt_transform").resolve(),
    packaged_project_dir=Path(__file__).joinpath("..", "dbt_project").resolve(),
)
transformation_project.prepare_if_dev()


# If DAGSTER_DBT_PARSE_PROJECT_ON_LOAD is set, a manifest will be created at runtime.
# Otherwise, we expect a manifest to be present in the project's target directory.

if os.getenv("DAGSTER_DBT_PARSE_PROJECT_ON_LOAD"):
    # Run dbt parse to generate the manifest. Adjust these calls based on your DbtCliResource's behavior.
    dbt_parse_invocation = DbtCliResource(project_dir=transformation_project).cli(
        ["parse"]
    )
    dbt_manifest_path = dbt_parse_invocation.target_path.joinpath("manifest.json")
else:
    dbt_manifest_path = transformation_project.project_dir.joinpath(
        "target", "manifest.json"
    )


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
