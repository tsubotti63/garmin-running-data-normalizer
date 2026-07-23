from __future__ import annotations

import struct

from garmin_running_data_normalizer.fit.parser import fit_crc16


def _definition(local: int, global_message: int, fields: list[tuple[int, int, int]]) -> bytes:
    return (
        bytes([0x40 | local, 0x00, 0x00])
        + struct.pack("<H", global_message)
        + bytes([len(fields)])
        + b"".join(bytes(field) for field in fields)
    )


def _record(local: int, values: bytes) -> bytes:
    return bytes([local]) + values


def synthetic_fit(
    *,
    sessions: int = 1,
    header_size: int = 14,
    header_crc_present: bool = True,
    invalid_header_crc: bool = False,
    invalid_file_crc: bool = False,
    invalid_metrics: bool = False,
    declared_laps_per_session: int = 1,
) -> bytes:
    """Create a visibly synthetic FIT activity without using user data."""
    session_fields = [
        (2, 4, 0x86), (5, 1, 0x00), (6, 1, 0x00),
        (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86),
        (11, 2, 0x84), (14, 4, 0x86), (15, 4, 0x86),
        (16, 1, 0x02), (17, 1, 0x02), (18, 1, 0x02),
        (19, 1, 0x02), (20, 2, 0x84), (21, 2, 0x84),
        (22, 2, 0x84), (23, 2, 0x84), (26, 2, 0x84),
    ]
    lap_fields = [
        (2, 4, 0x86), (7, 4, 0x86), (8, 4, 0x86),
        (9, 4, 0x86), (13, 4, 0x86), (14, 4, 0x86),
        (15, 1, 0x02), (16, 1, 0x02), (17, 1, 0x02),
        (18, 1, 0x02), (19, 2, 0x84), (20, 2, 0x84),
        (21, 2, 0x84), (22, 2, 0x84),
    ]
    u32_metric = 0xFFFFFFFF if invalid_metrics else 3_000
    u16_metric = 0xFFFF if invalid_metrics else 250
    u8_metric = 0xFF if invalid_metrics else 150
    body = bytearray(_definition(0, 18, session_fields))
    body.extend(_definition(1, 19, lap_fields))
    for ordinal in range(sessions):
        start = 1_000_000 + ordinal * 10_000
        body.extend(
            _record(
                0,
                b"".join(
                    [
                        struct.pack("<I", start),
                        bytes([1, 7]),
                        struct.pack("<II", 3_600_000, 3_500_000),
                        struct.pack("<I", 1_000_000 + ordinal * 100),
                        struct.pack("<H", 0xFFFF if invalid_metrics else 600),
                        struct.pack(
                            "<II",
                            u32_metric,
                            5_000 if not invalid_metrics else 0xFFFFFFFF,
                        ),
                        bytes(
                            [
                                u8_metric,
                                180 if not invalid_metrics else 0xFF,
                                82 if not invalid_metrics else 0xFF,
                                95 if not invalid_metrics else 0xFF,
                            ]
                        ),
                        struct.pack(
                            "<HHHHH",
                            u16_metric,
                            400 if not invalid_metrics else 0xFFFF,
                            100 if not invalid_metrics else 0xFFFF,
                            80 if not invalid_metrics else 0xFFFF,
                            declared_laps_per_session,
                        ),
                    ]
                ),
            )
        )
        body.extend(
            _record(
                1,
                b"".join(
                    [
                        struct.pack(
                            "<IIIIII",
                            start,
                            3_600_000,
                            3_500_000,
                            1_000_000 + ordinal * 100,
                            u32_metric,
                            5_000 if not invalid_metrics else 0xFFFFFFFF,
                        ),
                        bytes(
                            [
                                u8_metric,
                                180 if not invalid_metrics else 0xFF,
                                82 if not invalid_metrics else 0xFF,
                                95 if not invalid_metrics else 0xFF,
                            ]
                        ),
                        struct.pack(
                            "<HHHH",
                            u16_metric,
                            400 if not invalid_metrics else 0xFFFF,
                            100 if not invalid_metrics else 0xFFFF,
                            80 if not invalid_metrics else 0xFFFF,
                        ),
                    ]
                ),
            )
        )
    base_header = (
        bytes([header_size, 0x20])
        + struct.pack("<H", 0)
        + struct.pack("<I", len(body))
        + b".FIT"
    )
    if header_size == 14:
        header_crc = fit_crc16(base_header) if header_crc_present else 0
        if invalid_header_crc:
            header_crc ^= 0xFFFF
        header = base_header + struct.pack("<H", header_crc)
    else:
        header = base_header
    payload = header + bytes(body)
    file_crc = fit_crc16(payload)
    if invalid_file_crc:
        file_crc ^= 0xFFFF
    return payload + struct.pack("<H", file_crc)


def truncated_fit() -> bytes:
    return synthetic_fit()[:-3]


def unsupported_chained_fit() -> bytes:
    return synthetic_fit() + synthetic_fit()
