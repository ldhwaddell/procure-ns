import os
from pathlib import Path

import dagster as dg

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets
from transformation.project import transformation_project

log = dg.get_dagster_logger()

# transformation_project = DbtProject(
#     project_dir=Path(__file__).joinpath("..", "dbt_transform").resolve(),
#     packaged_project_dir=Path(__file__).joinpath("..", "dbt_project").resolve(),
# )
#
# log.info(f"project_dur: {Path(__file__).joinpath('..', 'dbt_transform').resolve()}")
# log.info(f"packaged_dir: {Path(__file__).joinpath('..', 'dbt_transform').resolve()}")
#
# # If DAGSTER_DBT_PARSE_PROJECT_ON_LOAD is set, a manifest will be created at runtime.
# # Otherwise, we expect a manifest to be present in the project's target directory.
#
# if os.getenv("DAGSTER_DBT_PARSE_PROJECT_ON_LOAD"):
#     log.info("PARSE ENV VAR SET")
#     # Run dbt parse to generate the manifest. Adjust these calls based on your DbtCliResource's behavior.
#     dbt_parse_invocation = (
#         DbtCliResource(project_dir=transformation_project).cli(["parse"]).wait()
#     )
#     log.info(dbt_parse_invocation)
#     dbt_manifest_path = dbt_parse_invocation.target_path.joinpath("manifest.json")
#     log.info(dbt_manifest_path)
# else:
#     dbt_manifest_path = transformation_project.project_dir.joinpath(
#         "target", "manifest.json"
#     )
#     log.info(dbt_manifest_path)
#


@dbt_assets(manifest=Path("transformation", "dbt_project", "target", "manifest.json"))
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
