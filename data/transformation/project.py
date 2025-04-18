from pathlib import Path
from dagster_dbt import DbtProject

project_dir = (
    Path("dbt_transform")
    if Path("dbt_transform").exists()
    else Path("packaged_dbt_project")
)

transformation_project = DbtProject(
    project_dir=project_dir,
    packaged_project_dir=Path("packaged_dbt_project"),
)
