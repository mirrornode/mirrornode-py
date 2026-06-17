#!/usr/bin/env python3
"""MIRRORNODE :: Ed25519 Key Generation Utility
Alias entry point expected by thoth_preflight check 3.2.
Delegates to gen_ed25519_key.py logic.

Usage:
    poetry run python3 scripts/generate_keys.py [--key-name <name>]
"""
import sys
from pathlib import Path

# Allow direct invocation from repo root
sys.path.insert(0, str(Path(__file__).parent))
from gen_ed25519_key import generate_keypair
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Ed25519 keypair into Oracle Vault")
    parser.add_argument("--key-name", default="mirrornode_node", help="Base filename for the keypair")
    args = parser.parse_args()
    generate_keypair(args.key_name)
