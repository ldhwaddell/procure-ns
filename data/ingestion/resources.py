import random
import socket

import dagster as dg

from ingestion.utils import ProxyConf


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
