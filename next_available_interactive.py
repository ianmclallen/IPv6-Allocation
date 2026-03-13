#!/usr/bin/env python3
"""
Next Available IPv6 Subnet Allocation (Interactive)

Sequentially enumerates child subnets of a parent IPv6 network by calling
IPv6Network.subnets(new_prefix=<...>) and emitting every `increment`-th subnet
starting at `start_index`. Prompts the user for all inputs.
"""

from __future__ import annotations

__version__ = "2.0.0"
__date__ = "2025-06-03"
__author__ = "Ian McLallen"
__email__ = "imclallen@infoblox.com"
__maintainer__ = "Ian McLallen"
__status__ = "Development"
__license__ = "BSD"


import sys
import time
from ipaddress import IPv6Network
from typing import Iterable, Iterator, Optional


# ---------------------------
# Validation & core utilities
# ---------------------------

def validate_inputs(parent_cidr: str, new_prefix: int, start_index: int, increment: int, count: int) -> IPv6Network:
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

    total_children = 1 << (new_prefix - parent.prefixlen)
    if start_index >= total_children:
        raise ValueError(
            f"Start index {start_index} is beyond the number of available children ({total_children})."
        )

    return parent


def maybe_confirm_large(parent: IPv6Network, new_prefix: int, count: int, auto_yes: bool) -> None:
    gap = new_prefix - parent.prefixlen
    total_children = 1 << gap
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
    gen = parent.subnets(new_prefix=new_prefix)

    # Skip to start_index
    for _ in range(start_index):
        try:
            next(gen)
        except StopIteration:
            return

    emitted = 0
    while emitted < count:
        try:
            subnet = next(gen)
        except StopIteration:
            break
        yield subnet
        emitted += 1

        # Skip the next (increment-1) subnets
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
# Prompts
# ---------------------------

def _prompt_non_empty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
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


def _prompt_non_negative_int(prompt: str) -> int:
    while True:
        s = _prompt_non_empty(prompt)
        try:
            n = int(s)
            if n < 0:
                raise ValueError
            return n
        except ValueError:
            print("Please enter a non-negative integer (>= 0).")


def _prompt_yes_no(prompt: str, default_no: bool = True) -> bool:
    ans = input(prompt).strip().lower()
    if not ans:
        return not default_no
    return ans in ("y", "yes", "true", "t", "1")


def get_user_inputs() -> tuple[str, int, int, int, int, Optional[str], bool]:
    print("=== Next Available IPv6 Subnet Allocation ===")
    parent_cidr = _prompt_non_empty("Parent IPv6 network (e.g., 2001:db8::/44): ")
    new_prefix = _prompt_positive_int("Child prefix length (e.g., 48): ")
    start_index = _prompt_non_negative_int("Start index (0-based): ")
    increment = _prompt_positive_int("Increment (emit every N'th subnet; e.g., 1): ")
    count = _prompt_positive_int("How many subnets to create?: ")
    output = input("Output file path (optional; press Enter to skip): ").strip() or None
    auto_yes = _prompt_yes_no("Auto-continue for large jobs? [y/N]: ", default_no=True)
    return parent_cidr, new_prefix, start_index, increment, count, output, auto_yes


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    start_time = time.time()

    parent_cidr, new_prefix, start_index, increment, count, output, auto_yes = get_user_inputs()

    try:
        parent = validate_inputs(parent_cidr, new_prefix, start_index, increment, count)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    maybe_confirm_large(parent, new_prefix, count, auto_yes=auto_yes)

    try:
        results = list(enumerate_next_available(parent, new_prefix, start_index, increment, count))
    except Exception as e:
        print(f"Allocation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAllocated subnets:")
    for net in results:
        print(net)

    if output:
        try:
            write_output(results, output)
            print(f"\nSaved {len(results)} subnet(s) to: {output}")
        except Exception as e:
            print(f"Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n--- {elapsed:.3f} seconds ---")


if __name__ == "__main__":
    main()
