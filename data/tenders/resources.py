import dagster as dg

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DataWarehouseResource(dg.ConfigurableResource):
    username: str
    password: str
    db: str

    def _url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.username}:{self.password}@dwh:5432/{self.db}"
        )

    def get_session(self) -> sessionmaker[Session]:
        engine = create_engine(self._url(), echo=False)
        return sessionmaker(bind=engine)
