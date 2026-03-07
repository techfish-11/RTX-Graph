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

    # Use 32-bit counters (ifInOctets/ifOutOctets); widely supported.
    # ifHCInOctets/ifHCOutOctets (64-bit) are not supported on many devices including Yamaha RTX.
    in_oid = ObjectType(ObjectIdentity(f"1.3.6.1.2.1.2.2.1.10.{if_index}"))
    out_oid = ObjectType(ObjectIdentity(f"1.3.6.1.2.1.2.2.1.16.{if_index}"))

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
    for oid, value in var_binds:
        # attempt to interpret counter value; handle common non-numeric responses
        if isinstance(value, Integer):
            values.append(int(value))
            continue

        text = value.prettyPrint()
        if text is None or text == "":
            raise SNMPError(f"invalid SNMP value for {oid}: <empty>")

        # sometimes devices return a message like "No Such Instance..."
        try:
            num = int(text)
        except ValueError:
            raise SNMPError(f"invalid SNMP value for {oid}: {text!r}")
        else:
            values.append(num)

    if len(values) != 2:
        raise SNMPError("SNMP response does not include in/out counters")

    return values[0], values[1]
