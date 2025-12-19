import gzip
import json
import logging
from pathlib import Path

import requests
import typer
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapError, OldapErrorNotFound
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.user import User

log = logging.getLogger(__name__)

def import_trig(
    graphdb_base: str,
    repo: str,
    trig_str: str,
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
):
    url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
    r = requests.post(
        url,
        data=trig_str.encode("utf-8"),
        headers={"Content-Type": "application/trig"},
        auth=auth,
        timeout=timeout,
    )
    if r.status_code != 200:
        log.error(f"ERROR: Request to '{url}' failed with status code {r.status_code}")
        raise typer.Exit(code=1)


def import_trig_gz(
    graphdb_base: str,
    repo: str,
    trig_gz: bytes,
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
):
    url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
    r = requests.post(
        url,
        data=trig_gz,
        headers={
            "Content-Type": "application/trig",
            "Content-Encoding": "gzip",
        },
        auth=auth,
        timeout=timeout,
    )
    if r.status_code < 200 or r.status_code >= 300:
        log.error(f"ERROR: Request to '{url}' failed with status code {r.status_code}")
        raise typer.Exit(code=1)


def load_project(graphdb_base: str,
                 repo: str,
                 inf: Path,
                 user: str,
                 password: str,
                 graphdb_user: str | None = None,
                 graphdb_password: str | None = None) -> None:
    cache = CacheSingletonRedis()
    cache.clear()

    with open(inf, "rb") as f:
        import_trig_gz(graphdb_base=graphdb_base,
                       repo=repo,
                       auth=(graphdb_user, graphdb_password) if graphdb_user and graphdb_password else None,
                       trig_gz=f.read())

    try:
        con = Connection(server=graphdb_base,
                         repo=repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)

    with gzip.open(inf, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith('#>>'):
                user_json = line[3:].strip()
                user = json.loads(user_json, object_hook=serializer.make_decoder_hook(connection=con))
                try:
                    existing_user = User.read(con=con, userId=user.userId)
                except OldapErrorNotFound:
                    # user does not exist -> create it
                    user.create(keep_dates=True)
                    log.info(f"Created user {user.userId}")
                else:
                    # user exists -> update it
                    if user.hasPermissions != existing_user.hasPermissions or user.inProject != existing_user.inProject:
                        existing_user.delete()
                        user.create(keep_dates=True)
                        log.info(f"Updated (replaced) user {user.userId}")
                    pass
            if line.startswith('#<<'):
                break


