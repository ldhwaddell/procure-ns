import os
import random
import socket
from dotenv import load_dotenv
from typing import Dict


def rand(min: int = 1, max: int = 4):
    """Get a random interval in [min, max]"""
    return random.uniform(min, max)


def resolve_proxy_ip() -> str:
    return socket.gethostbyname("brd.superproxy.io")


def get_proxy_conf(proxy_ip: str) -> Dict[str, str]:
    load_dotenv()
    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")
    port = 33335
    session_id = str(random.random())

    return {
        "server": f"{proxy_ip}:{port}",
        "username": f"{username}-session-{session_id}",
        "password": password,
    }
