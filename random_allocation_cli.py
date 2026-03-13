#!/usr/bin/env python3
"""
Random IPv6 Subnet Allocation

Generates N random child subnets of a given IPv6 network, at a new (longer) prefix length.
Can print to stdout and/or write results to a text file (one CIDR per line).

__version__ = '1.5.0'
__date__ = '03/13/2026'
__author__ = 'Ian McLallen'
__email__ = 'imclallen@infoblox.com'
__maintainer__ = 'Ian McLallen'
__status__ = 'Development'
__credits__ = ""
__license__ = 'BSD'
"""

from __future__ import annotations

import argparse
import ipaddress
import math
import random
import sys
import time
from typing import Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Randomly allocate IPv6 child subnets at a longer prefix."
    )
    parser.add_argument(
        "-n", "--network",
        required=True,
        help="IPv6 network in CIDR notation (e.g., 2001:db8::/48)."
    )
    parser.add_argument(
        "-p", "--new-prefix",
        required=True,
        help="Desired child subnet prefix (e.g., /64). Must be longer than the input network prefix."
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=1,
        help="Number of child subnets to generate (default: 1)."
    )
    parser.add_argument(
        "-o", "--output",
        help="Optional path to a text file; if provided, results are written here (one subnet per line)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional RNG seed for reproducible allocations."
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-continue without confirmation when the prefix gap is large."
    )
    return parser.parse_args()


def validate_inputs(parent: str, new_prefix_str: str, count: int) -> Tuple[ipaddress.IPv6Network, int]:
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

    # Ensure count does not exceed the number of available child subnets
    total_children = 1 << (new_prefix - parent_net.prefixlen)  # 2 ** gap
    if count > total_children:
        raise ValueError(
            f"Requested {count} subnets but only {total_children} are available between /{parent_net.prefixlen} and /{new_prefix}."
        )

    return parent_net, new_prefix


def maybe_confirm_large_gap(parent: ipaddress.IPv6Network, new_prefix: int, auto_yes: bool) -> None:
    """Warn or confirm when the prefix gap is large (e.g., >= 24)."""
    gap = new_prefix - parent.prefixlen
    if gap >= 24 and not auto_yes:
        total_children = 1 << gap
        print(
            f"\nThe difference between prefixes is large: /{parent.prefixlen} -> /{new_prefix} (gap {gap}).\n"
            f"That creates {total_children:,} possible child subnets.\n"
        )
        resp = input("Continue? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborting.")
            sys.exit(0)


def pick_child_indices(total_children: int, count: int, rng: random.Random) -> List[int]:
    """
    Efficiently pick `count` unique child-subnet indices in [0, total_children).

    Uses random.sample over range(total_children) when count < total_children,
    which avoids building a massive list in memory. If count == total_children,
    we return all indices.
    """
    if count == total_children:
        # Avoid creating a giant list; iterate as range and convert only if needed elsewhere
        return list(range(total_children))
    return rng.sample(range(total_children), count)


def child_index_to_network(parent: ipaddress.IPv6Network, new_prefix: int, idx: int) -> ipaddress.IPv6Network:
    """
    Convert an index (0..2^(gap)-1) into the corresponding child subnet of `parent` at `new_prefix`.
    """
    gap = new_prefix - parent.prefixlen
    # Shift index into the correct bit position and OR with the parent network address.
    parent_int = int(parent.network_address)
    child_network_int = (parent_int & ((1 << 128) - (1 << (128 - parent.prefixlen)))) | (idx << (128 - new_prefix))
    return ipaddress.IPv6Network((ipaddress.IPv6Address(child_network_int), new_prefix))


def allocate_random_subnets(
    parent: ipaddress.IPv6Network,
    new_prefix: int,
    count: int,
    seed: int | None = None
) -> List[ipaddress.IPv6Network]:
    rng = random.Random(seed)
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap

    # Quick info message (kept as print for CLI UX; could be switched to logging if preferred)
    print(f"\nParent network: {parent} (/{parent.prefixlen})")
    print(f"New prefix: /{new_prefix}  |  Gap: {gap}  |  Available: {total_children:,}  |  Requested: {count}")

    indices = pick_child_indices(total_children, count, rng)
    # Map each index to the actual child subnet
    return [child_index_to_network(parent, new_prefix, i) for i in indices]


def write_output(subnets: Iterable[ipaddress.IPv6Network], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for net in subnets:
            fh.write(f"{net}\n")


def main() -> None:
    args = parse_args()
    start = time.time()

    try:
        parent_net, new_prefix = validate_inputs(args.network, args.new_prefix, args.count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    maybe_confirm_large_gap(parent_net, new_prefix, auto_yes=args.yes)

    try:
        subnets = allocate_random_subnets(parent_net, new_prefix, args.count, seed=args.seed)
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Print results to stdout
    print("\nAllocated subnets:")
    for net in subnets:
        print(net)

    # Optionally write to file
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
