from pathlib import Path
from dagster_dbt import DbtProject

transformation_project = DbtProject(
    # project_dir=Path(__file__).joinpath("..", "dbt_transform").resolve(),
    # packaged_project_dir=Path(__file__).joinpath("..", "packaged_dbt_project").resolve(),
    project_dir=Path("dbt_transform"),
    packaged_project_dir=Path("packaged_dbt_project"),
)
