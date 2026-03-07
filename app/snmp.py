from __future__ import annotations

from typing import Tuple

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    Integer,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)


class SNMPError(RuntimeError):
    pass


def fetch_interface_counters(
    host: str,
    community: str,
    if_index: int,
    version: str = "2c",
    port: int = 161,
    timeout: int = 2,
    retries: int = 1,
) -> Tuple[int, int]:
    if version not in {"2c", "v2c"}:
        raise SNMPError(f"Unsupported SNMP version: {version}")

    in_oid = ObjectType(ObjectIdentity(f"1.3.6.1.2.1.31.1.1.1.6.{if_index}"))
    out_oid = ObjectType(ObjectIdentity(f"1.3.6.1.2.1.31.1.1.1.10.{if_index}"))

    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        UdpTransportTarget((host, port), timeout=timeout, retries=retries),
        ContextData(),
        in_oid,
        out_oid,
    )

    error_indication, error_status, error_index, var_binds = next(iterator)

    if error_indication:
        raise SNMPError(str(error_indication))
    if error_status:
        raise SNMPError(f"{error_status.prettyPrint()} at index {error_index}")

    values: list[int] = []
    for _, value in var_binds:
        if isinstance(value, Integer):
            values.append(int(value))
        else:
            try:
                values.append(int(value.prettyPrint()))
            except ValueError as exc:
                raise SNMPError(f"invalid SNMP value: {value}") from exc

    if len(values) != 2:
        raise SNMPError("SNMP response does not include in/out counters")

    return values[0], values[1]
