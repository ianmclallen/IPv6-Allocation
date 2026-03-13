#!/usr/bin/env python3
"""
Next Available IPv6 Subnet Allocation (CLI)

Sequentially enumerates child subnets of a parent IPv6 network
by calling IPv6Network.subnets(new_prefix=<...>) and emitting
every `increment`-th subnet starting at `start_index`.

Example:
  python next_available_cli.py \
      -n 2001:db8::/44 -p 48 -s 0 -i 1 -c 10 -o ./next_avail.txt -y
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
import sys
import time
from ipaddress import IPv6Network
from typing import Iterable, Iterator, Optional


# ---------------------------
# Validation & core utilities
# ---------------------------

def validate_inputs(parent_cidr: str, new_prefix: int, start_index: int, increment: int, count: int) -> IPv6Network:
    """Validate inputs and return the parsed parent IPv6 network."""
    try:
        parent = IPv6Network(parent_cidr, strict=False)
    except Exception as e:
        raise ValueError(f"Invalid IPv6 network '{parent_cidr}': {e}") from e

    if not (0 <= new_prefix <= 128):
        raise ValueError("New prefix must be between /0 and /128.")

    if parent.prefixlen >= new_prefix:
        raise ValueError(
            f"New prefix /{new_prefix} must be LONGER (numerically greater) than the parent /{parent.prefixlen}."
        )

    if start_index < 0:
        raise ValueError("Start index must be >= 0.")

    if increment <= 0:
        raise ValueError("Increment must be a positive integer.")

    if count <= 0:
        raise ValueError("Count must be a positive integer.")

    # Feasibility check: at least ensure there exists a first element
    total_children = 1 << (new_prefix - parent.prefixlen)
    if start_index >= total_children:
        raise ValueError(
            f"Start index {start_index} is beyond the number of available children ({total_children})."
        )

    return parent


def maybe_confirm_large(parent: IPv6Network, new_prefix: int, count: int, auto_yes: bool) -> None:
    """Ask for confirmation when the job looks large."""
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap

    # Heuristic: if requesting many or the space is large, confirm unless -y
    if not auto_yes and (gap >= 18 or count >= 5000 or total_children >= 1 << 24):
        print(
            f"\nWarning: /{parent.prefixlen} -> /{new_prefix} (gap {gap}) "
            f"yields {total_children:,} child subnets."
        )
        resp = input("Continue? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborting.")
            sys.exit(0)


def enumerate_next_available(
    parent: IPv6Network,
    new_prefix: int,
    start_index: int,
    increment: int,
    count: int,
) -> Iterator[IPv6Network]:
    """
    Stream `count` subnets from the generator returned by parent.subnets(new_prefix=...),
    starting at `start_index` and then taking every `increment`-th entry.
    """
    # ipaddress.subnets() returns a generator; skip to the first wanted index efficiently
    gen = parent.subnets(new_prefix=new_prefix)

    # Skip the first `start_index` elements
    for _ in range(start_index):
        try:
            next(gen)
        except StopIteration:
            return

    # Now yield one, then skip increment-1, etc.
    emitted = 0
    while emitted < count:
        try:
            subnet = next(gen)
        except StopIteration:
            break
        yield subnet
        emitted += 1
        # Skip increment-1 subnets
        for _ in range(increment - 1):
            try:
                next(gen)
            except StopIteration:
                return


def write_output(subnets: Iterable[IPv6Network], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for net in subnets:
            fh.write(f"{net}\n")


# ---------------------------
# CLI
# ---------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Next Available (sequential) IPv6 subnet allocator."
    )
    p.add_argument("-n", "--network", required=True, help="Parent IPv6 network (e.g., 2001:db8::/44)")
    p.add_argument("-p", "--new-prefix", type=int, required=True, help="Child prefix length (e.g., 48)")
    p.add_argument("-s", "--start", type=int, default=0, help="Start index within the child space (default: 0)")
    p.add_argument("-i", "--increment", type=int, default=1, help="Enumerate every Nth subnet (default: 1)")
    p.add_argument("-c", "--count", type=int, default=1, help="How many subnets to emit (default: 1)")
    p.add_argument("-o", "--output", help="Optional path to a text file (one subnet CIDR per line)")
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation for large jobs")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    start_time = time.time()

    try:
        parent = validate_inputs(args.network, args.new_prefix, args.start, args.increment, args.count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    maybe_confirm_large(parent, args.new_prefix, args.count, auto_yes=args.yes)

    try:
        # First, materialize the results for optional file writing and printing
        results = list(
            enumerate_next_available(parent, args.new_prefix, args.start, args.increment, args.count)
        )
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAllocated subnets:")
    for net in results:
        print(net)

    if args.output:
        try:
            write_output(results, args.output)
            print(f"\nSaved {len(results)} subnet(s) to: {args.output}")
        except Exception as e:
            print(f"Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n--- {elapsed:.3f} seconds ---")


if __name__ == "__main__":
    main()
