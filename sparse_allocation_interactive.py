#!/usr/bin/env python3
"""
Sparse IPv6 Subnet Allocation (Interactive)

Deterministically generates N child subnets of a given IPv6 parent network
using a sparse bit-reversal allocation order. Prompts for inputs.
"""

from __future__ import annotations

__version__ = "2.0.0"
__date__ = "2026-03-13"
__author__ = "Ian McLallen"
__email__ = "imclallen@infoblox.com"
__maintainer__ = "Ian McLallen"
__status__ = "Development"
__license__ = "BSD"


import ipaddress
import sys
import time
from typing import Iterable, List, Tuple, Optional


# ---------------------------
# Validation & core utilities (same as CLI)
# ---------------------------

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

    total_children = 1 << (new_prefix - parent_net.prefixlen)
    if count > total_children:
        raise ValueError(
            f"Requested {count} subnets but only {total_children} are available between "
            f"/{parent_net.prefixlen} and /{new_prefix}."
        )

    return parent_net, new_prefix


def maybe_confirm_large(parent: ipaddress.IPv6Network, new_prefix: int, count: int, auto_yes: bool) -> None:
    gap = new_prefix - parent.prefixlen
    if (gap >= 18 or count >= 5000) and not auto_yes:  # mirrors original intent  [1](https://infoblox-my.sharepoint.com/personal/imclallen_infoblox_com/Documents/Microsoft%20Copilot%20Chat%20Files/Sparse_Allocation.py)
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
    r = 0
    for _ in range(width):
        r = (r << 1) | (x & 1)
        x >>= 1
    return r


def child_index_to_network(parent: ipaddress.IPv6Network, new_prefix: int, idx: int) -> ipaddress.IPv6Network:
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap
    if not (0 <= idx < total_children):
        raise ValueError(f"Index {idx} out of bounds for gap {gap} (0..{total_children-1}).")

    parent_base = int(parent.network_address)
    child_network_int = parent_base | (idx << (128 - new_prefix))
    return ipaddress.IPv6Network((ipaddress.IPv6Address(child_network_int), new_prefix))


def allocate_sparse_subnets(
    parent: ipaddress.IPv6Network,
    new_prefix: int,
    count: int
) -> List[ipaddress.IPv6Network]:
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
# Interactive prompts
# ---------------------------

def _prompt_non_empty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty. Please try again.")


def _prompt_positive_int(prompt: str) -> int:
    while True:
        s = _prompt_non_empty(prompt)
        try:
            n = int(s)
            if n <= 0:
                raise ValueError
            return n
        except ValueError:
            print("Please enter a positive integer.")


def _prompt_yes_no(prompt: str, default_no: bool = True) -> bool:
    ans = input(prompt).strip().lower()
    if not ans:
        return not default_no
    return ans in ("y", "yes", "true", "t", "1")


def get_user_inputs() -> tuple[str, str, int, Optional[str], bool]:
    print("=== Sparse IPv6 Subnet Allocation ===")
    parent_network = _prompt_non_empty("Parent IPv6 network (e.g., 2001:db8::/32): ")
    new_prefix = _prompt_non_empty("Child prefix (e.g., /60): ")
    count = _prompt_positive_int("How many child subnets? (positive integer): ")
    output_path = input("Output file path (optional; press Enter to skip): ").strip() or None
    auto_yes = _prompt_yes_no("Auto-continue for large gap/count? [y/N]: ", default_no=True)
    return parent_network, new_prefix, count, output_path, auto_yes


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    start = time.time()

    parent_str, new_prefix_str, count, output_path, auto_yes = get_user_inputs()

    try:
        parent_net, new_prefix = validate_inputs(parent_str, new_prefix_str, count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    maybe_confirm_large(parent_net, new_prefix, count, auto_yes=auto_yes)

    try:
        subnets = allocate_sparse_subnets(parent_net, new_prefix, count)
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAllocated subnets:")
    for net in subnets:
        print(net)

    if output_path:
        try:
            write_output(subnets, output_path)
            print(f"\nSaved {len(subnets)} subnet(s) to: {output_path}")
        except Exception as e:
            print(f"Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)

    elapsed = time.time() - start
    print(f"\n--- {elapsed:.3f} seconds ---")


if __name__ == "__main__":
    main()
