"""Small SQL execution layer. All values are bound parameters, never SQL fragments."""

from dataclasses import fields
from typing import Any, Mapping, TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


T = TypeVar("T")


def _map(row_type: type[T], row: Mapping[str, Any]) -> T:
    return row_type(**{field.name: row[field.name] for field in fields(row_type) if field.name in row})


async def query(session: AsyncSession, sql: str, params: Mapping[str, Any], row_type: type[T]) -> list[T]:
    result = await session.execute(text(sql), dict(params))
    return [_map(row_type, row) for row in result.mappings().all()]


async def query_one(session: AsyncSession, sql: str, params: Mapping[str, Any], row_type: type[T]) -> T | None:
    result = await session.execute(text(sql), dict(params))
    row = result.mappings().first()
    return _map(row_type, row) if row is not None else None


async def scalar(session: AsyncSession, sql: str, params: Mapping[str, Any] | None = None) -> Any:
    result = await session.execute(text(sql), dict(params or {}))
    return result.scalar()


async def execute(session: AsyncSession, sql: str, params: Mapping[str, Any] | None = None) -> Any:
    return await session.execute(text(sql), dict(params or {}))


def where(values: Mapping[str, Any], allowed: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    """Build equality predicates from a fixed, caller-owned column whitelist."""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for name, value in values.items():
        if name not in allowed:
            raise ValueError(f"Filter is not whitelisted: {name}")
        if value is not None:
            clauses.append(f"{allowed[name]} = :filter_{name}")
            params[f"filter_{name}"] = value
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


VERSIONED_COLUMNS: dict[str, frozenset[str]] = {
    "customers": frozenset({"kyc_status", "kyc_verified_at"}),
    "accounts": frozenset({"balance", "status"}),
    "invoices": frozenset({"status", "paid_at"}),
}


async def update_versioned(
    session: AsyncSession,
    table: str,
    row_id: int,
    expected_version: int,
    values: Mapping[str, Any],
) -> int | None:
    """Update a versioned row; return its new version or None on a conflict.

    The existing schema calls the optimistic-lock column ``version`` rather than
    ``row_version``. Table and column names come only from this static whitelist.
    """
    if table not in VERSIONED_COLUMNS or not values or not set(values) <= VERSIONED_COLUMNS[table]:
        raise ValueError("Unsafe versioned update")
    assignments = ", ".join(f"{column} = :set_{column}" for column in values)
    params = {f"set_{column}": value for column, value in values.items()}
    params.update({"row_id": row_id, "expected_version": expected_version})
    return await scalar(
        session,
        f"UPDATE {table} SET {assignments}, version = version + 1, updated_at = now() "
        "WHERE id = :row_id AND version = :expected_version RETURNING version",
        params,
    )
