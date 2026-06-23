from math import ceil


def memory_sized_host_gas(rate_per_1024_octets: int, octets: int) -> int:
    """GP v0.8.0 host memory gas: G(L, l) = ceil(L * l / 1024)."""
    return ceil(rate_per_1024_octets * octets / 1024)
