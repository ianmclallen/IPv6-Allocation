#!/usr/bin/env python3
"""
Sparse IPv6 Subnet Allocation (CLI)

Deterministically generates N child subnets of a given IPv6 parent network
using a sparse bit-reversal allocation order.
"""
from __future__ import annotations

__version__ = "2.0.0"
__date__ = "2025-06-03"
__author__ = "Ian McLallen"
__email__ = "imclallen@infoblox.com"
__maintainer__ = "Ian McLallen"
__status__ = "Development"
__license__ = "BSD"

import argparse
import ipaddress
import sys
import time
from typing import Iterable, List, Tuple


# ---------------------------
# Validation & core utilities
# ---------------------------

def validate_inputs(parent: str, new_prefix_str: str, count: int) -> Tuple[ipaddress.IPv6Network, int]:
    """Validate inputs and return (parent_network, new_prefix_int)."""
    try:
        parent_net = ipaddress.IPv6Network(parent, strict=False)
    except Exception as e:
        raise ValueError(f"Invalid IPv6 network '{parent}': {e}") from e

    if not new_prefix_str.startswith("/"):
        raise ValueError("New prefix must start with '/'. Example: /64")

    try:
        new_prefix = int(new_prefix_str[1:])
    except ValueError as e:
        raise ValueError(f"New prefix must be an integer after '/': {new_prefix_str}") from e

    if not (0 <= new_prefix <= 128):
        raise ValueError("New prefix must be between /0 and /128.")

    if new_prefix <= parent_net.prefixlen:
        raise ValueError(
            f"New prefix /{new_prefix} must be LONGER (numerically greater) than the parent /{parent_net.prefixlen}."
        )

    if count <= 0:
        raise ValueError("Count must be a positive integer.")

    total_children = 1 << (new_prefix - parent_net.prefixlen)
    if count > total_children:
        raise ValueError(
            f"Requested {count} subnets but only {total_children} are available between "
            f"/{parent_net.prefixlen} and /{new_prefix}."
        )

    return parent_net, new_prefix


def maybe_confirm_large(parent: ipaddress.IPv6Network, new_prefix: int, count: int, auto_yes: bool) -> None:
    """
    Confirm when the prefix gap (new - parent) is large or when the requested count is large.
    Mirrors the spirit of your original script, which protected against heavy workloads
    when the difference is big or the number of networks is high.  [1](https://infoblox-my.sharepoint.com/personal/imclallen_infoblox_com/Documents/Microsoft%20Copilot%20Chat%20Files/Sparse_Allocation.py)
    """
    gap = new_prefix - parent.prefixlen
    if (gap >= 18 or count >= 5000) and not auto_yes:
        total_children = 1 << gap
        print(
            f"\nWarning: /{parent.prefixlen} -> /{new_prefix} (gap {gap}) "
            f"creates {total_children:,} possible child networks.\n"
            "Iterating many subnets could be time and resource consuming.\n"
        )
        resp = input("Continue? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborting.")
            sys.exit(0)


def bit_reverse(x: int, width: int) -> int:
    """Return the bit-reversal of x for a fixed bit width."""
    r = 0
    for _ in range(width):
        r = (r << 1) | (x & 1)
        x >>= 1
    return r


def child_index_to_network(parent: ipaddress.IPv6Network, new_prefix: int, idx: int) -> ipaddress.IPv6Network:
    """
    Convert an index (0..2^(gap)-1) into the corresponding child subnet of `parent` at `new_prefix`.
    """
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap
    if not (0 <= idx < total_children):
        raise ValueError(f"Index {idx} out of bounds for gap {gap} (0..{total_children-1}).")

    parent_base = int(parent.network_address)             # already aligned to parent.prefixlen
    child_network_int = parent_base | (idx << (128 - new_prefix))
    return ipaddress.IPv6Network((ipaddress.IPv6Address(child_network_int), new_prefix))


def allocate_sparse_subnets(
    parent: ipaddress.IPv6Network,
    new_prefix: int,
    count: int
) -> List[ipaddress.IPv6Network]:
    """
    Generate `count` child subnets in *sparse* order:
    the i-th subnet is the child at index bit_reverse(i, gap).
    (Your original code built all reversed-bit patterns and took the first N; this is the same
    order without building an intermediate list.)  [1](https://infoblox-my.sharepoint.com/personal/imclallen_infoblox_com/Documents/Microsoft%20Copilot%20Chat%20Files/Sparse_Allocation.py)
    """
    gap = new_prefix - parent.prefixlen
    results: List[ipaddress.IPv6Network] = []
    for i in range(count):
        idx = bit_reverse(i, gap)
        results.append(child_index_to_network(parent, new_prefix, idx))
    return results


def write_output(subnets: Iterable[ipaddress.IPv6Network], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for net in subnets:
            fh.write(f"{net}\n")


# ---------------------------
# CLI
# ---------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sparse IPv6 child subnet allocator using bit-reversal ordering."
    )
    p.add_argument("-n", "--network", required=True, help="IPv6 parent network (e.g., 2001:db8::/32)")
    p.add_argument("-p", "--new-prefix", required=True, help="Desired child prefix (e.g., /60)")
    p.add_argument("-c", "--count", type=int, default=1, help="Number of child subnets (default: 1)")
    p.add_argument("-o", "--output", help="Optional path to a text file (one subnet CIDR per line)")
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation for large gap/count")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    start = time.time()

    try:
        parent_net, new_prefix = validate_inputs(args.network, args["new_prefix"] if isinstance(args, dict) else args.new_prefix, args.count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    maybe_confirm_large(parent_net, new_prefix, args.count, auto_yes=args.yes)

    try:
        subnets = allocate_sparse_subnets(parent_net, new_prefix, args.count)
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAllocated subnets:")
    for net in subnets:
        print(net)

    if args.output:
        try:
            write_output(subnets, args.output)
            print(f"\nSaved {len(subnets)} subnet(s) to: {args.output}")
        except Exception as e:
            print(f"Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)

    elapsed = time.time() - start
    print(f"\n--- {elapsed:.3f} seconds ---")


if __name__ == "__main__":
    main()
