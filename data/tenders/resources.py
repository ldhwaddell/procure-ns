import socket
import random

import dagster as dg

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from typing import Dict


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


class ProxyResource(dg.ConfigurableResource):
    username: str
    password: str

    def _resolve_proxy_ip(self) -> str:
        return socket.gethostbyname("brd.superproxy.io")

    def get_proxy_conf(self) -> Dict[str, str]:
        port = 33335
        session_id = str(random.random())

        return {
            "server": f"{self._resolve_proxy_ip()}:{port}",
            "username": f"{self.username}-session-{session_id}",
            "password": self.password,
        }
