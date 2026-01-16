"""
dbconnection.py

Oracle Database client using connection pool.
All DB + pool configuration is read from database.config
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
import oracledb


@dataclass(frozen=True)
class DBConfig:
    user: str
    password: str
    dsn: str
    oracle_client_lib_dir: Optional[str]
    min_pool_size: int
    max_pool_size: int
    increment: int
    timeout: Optional[int]
    wait_timeout: Optional[int]
    getmode: Optional[int]
    thick_client_fallback_dir: Optional[str]


def _to_int(val: Optional[str], default: Optional[int]) -> Optional[int]:
    return default if val in (None, "") else int(val)


def load_properties(path: str) -> Dict[str, str]:
    props: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            props[k.strip().lower()] = v.strip()
    return props


def load_db_config(path: str) -> DBConfig:
    p = load_properties(path)

    user = p.get("user") or p.get("user")
    password = p.get("password") or p.get("password")
    dsn = p.get("dsn")

    if not all([user, password, dsn]):
        raise ValueError("database config must define user/password/dsn")

    return DBConfig(
        user=user,
        password=password,
        dsn=dsn,
        oracle_client_lib_dir=p.get("oracle_client_lib_dir"),
        min_pool_size=int(p.get("min_pool_size", 1)),
        max_pool_size=int(p.get("max_pool_size", 5)),
        increment=int(p.get("increment", 1)),
        timeout=_to_int(p.get("timeout"), None),
        wait_timeout=_to_int(p.get("wait_timeout"), None),
        getmode=_to_int(p.get("getmode"), None),
        thick_client_fallback_dir=p.get("thick_client_fallback_dir"),
    )


class DatabaseClient:
    def __init__(self, cfg: DBConfig):
        lib_dir = cfg.oracle_client_lib_dir or cfg.thick_client_fallback_dir or os.getenv("ORACLE_CLIENT_LIB_DIR")
        if lib_dir:
            try:
                oracledb.init_oracle_client(lib_dir)
            except Exception:
                pass

        pool_kwargs: Dict[str, Any] = {}
        if cfg.timeout is not None:
            pool_kwargs["timeout"] = cfg.timeout
        if cfg.wait_timeout is not None:
            pool_kwargs["wait_timeout"] = cfg.wait_timeout
        if cfg.getmode is not None:
            pool_kwargs["getmode"] = cfg.getmode

        self._pool = oracledb.create_pool(
            user=cfg.user,
            password=cfg.password,
            dsn=cfg.dsn,
            min=cfg.min_pool_size,
            max=cfg.max_pool_size,
            increment=cfg.increment,
            **pool_kwargs,
        )

    @classmethod
    def from_properties(cls, path: str = "database.config") -> "DatabaseClient":
        return cls(load_db_config(path))

    def close(self) -> None:
        self._pool.close()

    def execute_select(self, sql: str, params: Optional[Dict[str, Any]] = None):
        with self._pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                cols = [c[0] for c in cur.description or []]
                return [
                    {cols[i]: (v.read() if isinstance(v, oracledb.LOB) else v) for i, v in enumerate(row)}
                    for row in cur.fetchall()
                ]

    def execute_dml(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        with self._pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or {})
                rc = cur.rowcount or 0
            conn.commit()
            return rc
