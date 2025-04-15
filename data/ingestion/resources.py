import random
import socket

import dagster as dg
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from ingestion.utils import ProxyConf


class DataWarehouseResource(dg.ConfigurableResource):
    username: str
    password: str
    db: str

    def _sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.username}:{self.password}@dwh:5432/{self.db}"
        )

    def _async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@dwh:5432/{self.db}"
        )

    def get_session(self) -> sessionmaker[Session]:
        engine = create_engine(self._sync_url(), echo=False)
        return sessionmaker(bind=engine)

    def get_async_session(self) -> async_sessionmaker[AsyncSession]:
        engine = create_async_engine(self._async_url(), echo=False)
        return async_sessionmaker(bind=engine)


class ProxyResource(dg.ConfigurableResource):
    username: str
    password: str

    def _resolve_proxy_ip(self) -> str:
        return socket.gethostbyname("brd.superproxy.io")

    def get_proxy_conf(self) -> ProxyConf:
        port = 33335
        session_id = str(random.random())

        return {
            "server": f"{self._resolve_proxy_ip()}:{port}",
            "username": f"{self.username}-session-{session_id}",
            "password": self.password,
        }
