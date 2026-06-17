#!/usr/bin/env python3
"""MIRRORNODE :: Ed25519 Key Generation Utility (3.2)
Generates an Ed25519 keypair and writes to Oracle Vault.

Usage:
    python3 scripts/gen_ed25519_key.py [--key-name <name>]
"""
import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

VAULT_DIR = Path.home() / ".mirrornode" / "oracle" / "keys"


def generate_keypair(key_name: str) -> tuple[Path, Path]:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    priv_path = VAULT_DIR / f"{key_name}.pem"
    pub_path = VAULT_DIR / f"{key_name}.pub.pem"

    priv_path.write_bytes(
        private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    pub_path.write_bytes(pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

    os.chmod(priv_path, 0o600)
    print(f"[gen_ed25519_key] Private key: {priv_path}")
    print(f"[gen_ed25519_key] Public  key: {pub_path}")
    return priv_path, pub_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Ed25519 keypair into Oracle Vault")
    parser.add_argument("--key-name", default="mirrornode_node", help="Base filename for the keypair")
    args = parser.parse_args()
    generate_keypair(args.key_name)
