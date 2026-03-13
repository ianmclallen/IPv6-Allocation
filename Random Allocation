#!/usr/bin/env python3
"""
Random IPv6 Subnet Allocation (Interactive)

Generates N random child subnets of a given IPv6 network, at a new (longer) prefix length.
Prompts the user for inputs instead of using command-line arguments.
"""

from __future__ import annotations

__version__ = '1.5.0'
__date__ = '03/13/2026'
__author__ = 'Ian McLallen'
__email__ = 'imclallen@infoblox.com'
__maintainer__ = 'Ian McLallen'
__status__ = 'Development'
__credits__ = ""
__license__ = 'BSD'


import ipaddress
import random
import secrets
import sys
import time
from typing import Iterable, List, Tuple, Optional


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

    total_children = 1 << (new_prefix - parent_net.prefixlen)  # 2 ** gap
    if count > total_children:
        raise ValueError(
            f"Requested {count} subnets but only {total_children} are available between "
            f"/{parent_net.prefixlen} and /{new_prefix}."
        )

    return parent_net, new_prefix


def maybe_confirm_large_gap(parent: ipaddress.IPv6Network, new_prefix: int, auto_yes: bool) -> None:
    """Warn or confirm when the prefix gap is large (>= 24)."""
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
    Uses random.sample over range(total_children) to avoid building large lists in memory.
    If count == total_children, return all indices.
    """
    if count == total_children:
        return list(range(total_children))
    return rng.sample(range(total_children), count)


def child_index_to_network(parent: ipaddress.IPv6Network, new_prefix: int, idx: int) -> ipaddress.IPv6Network:
    """
    Convert an index (0..2^(gap)-1) into the corresponding child subnet of `parent` at `new_prefix`.
    """
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap
    if not (0 <= idx < total_children):
        raise ValueError(f"Index {idx} out of bounds for gap {gap} (0..{total_children-1}).")

    parent_int = int(parent.network_address)
    # Mask to preserve parent prefix bits
    parent_masked = parent_int & ((1 << 128) - (1 << (128 - parent.prefixlen)))
    child_network_int = parent_masked | (idx << (128 - new_prefix))
    return ipaddress.IPv6Network((ipaddress.IPv6Address(child_network_int), new_prefix))


def allocate_random_subnets(
    parent: ipaddress.IPv6Network,
    new_prefix: int,
    count: int,
    seed: Optional[int] = None
) -> List[ipaddress.IPv6Network]:
    rng = random.Random(seed)
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap

    # Informational banner
    print(f"\nParent network: {parent} (/{parent.prefixlen})")
    print(f"New prefix: /{new_prefix}  |  Gap: {gap}  |  Available: {total_children:,}  |  Requested: {count}")
    if seed is None:
        print("RNG mode: non-deterministic (no seed provided)")
    else:
        print(f"RNG mode: deterministic (seed = {seed})")

    indices = pick_child_indices(total_children, count, rng)
    return [child_index_to_network(parent, new_prefix, i) for i in indices]


def write_output(subnets: Iterable[ipaddress.IPv6Network], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for net in subnets:
            fh.write(f"{net}\n")


# ---------------------------
# Interactive input collector
# ---------------------------

def _prompt_non_empty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty. Please try again.")


def _prompt_optional_int(prompt: str) -> Optional[int]:
    val = input(prompt).strip()
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        print("Not a valid integer. Leaving unset.")
        return None


def _prompt_yes_no(prompt: str, default_no: bool = True) -> bool:
    """
    Returns True for yes, False for no.
    If default_no is True, empty input returns False; otherwise True.
    """
    val = input(prompt).strip().lower()
    if not val:
        return not default_no
    return val in ("y", "yes", "true", "t", "1")


def _rng_help() -> None:
    print(
        "\n[RNG Help]\n"
        " - RNG stands for Random Number Generator.\n"
        " - If you provide a numeric seed, the same subnets will be chosen on every run "
        "(useful for debugging and reproducing results).\n"
        " - If you leave the seed blank, each run will produce different results.\n"
        " - Enter 'auto' to generate a secure random seed now (the script will print it so you can reuse it later).\n"
    )


def get_user_inputs() -> tuple[str, str, int, Optional[str], Optional[int], bool]:
    """
    Prompt the user for:
      - parent network (CIDR)
      - new prefix (e.g., /64)
      - count (positive int)
      - optional output file path
      - optional seed: integer, 'auto' to generate, or empty for none
      - auto-yes (bool) for large gaps
    """
    print("=== Random IPv6 Subnet Allocation ===")
    parent_network = _prompt_non_empty("Parent IPv6 network (e.g., 2001:db8::/48): ")
    new_prefix = _prompt_non_empty("New child prefix (e.g., /64): ")

    # Count with validation loop
    while True:
        count_str = _prompt_non_empty("How many child subnets do you want? (positive integer): ")
        try:
            count = int(count_str)
            if count <= 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a positive integer for the count.")

    output_path = input("Output file path (optional; press Enter to skip): ").strip() or None

    # RNG help and seed prompt (supports integer, 'auto', or empty)
    _rng_help()
    while True:
        seed_raw = input("Random Number Generated seed (integer | 'auto' to generate | Enter for none): ").strip().lower()
        if seed_raw == "":
            seed = None
            break
        if seed_raw == "auto":
            # Use cryptographically strong randomness for the seed, then print it
            seed = secrets.randbits(64)
            print(f"Generated Random Number Seed: {seed}  (save this value to reproduce the same results)")
            break
        try:
            seed = int(seed_raw)
            break
        except ValueError:
            print("Please enter a valid integer, 'auto', or press Enter to skip.")

    auto_yes = _prompt_yes_no("Auto-continue for large prefix gaps? [y/N]: ", default_no=True)

    return parent_network, new_prefix, count, output_path, seed, auto_yes


# -------------
# Main routine
# -------------

def main() -> None:
    start = time.time()

    # Collect interactive inputs
    parent_str, new_prefix_str, count, output_path, seed, auto_yes = get_user_inputs()

    # Validate inputs
    try:
        parent_net, new_prefix = validate_inputs(parent_str, new_prefix_str, count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    # Safety confirmation for very large gaps
    maybe_confirm_large_gap(parent_net, new_prefix, auto_yes=auto_yes)

    # Allocate
    try:
        subnets = allocate_random_subnets(parent_net, new_prefix, count, seed=seed)
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Print results to stdout
    print("\nAllocated subnets:")
    for net in subnets:
        print(net)

    # Optionally write to file
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
