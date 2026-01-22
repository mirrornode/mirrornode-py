#!/usr/bin/env python3
"""
MIRRORNODE :: Key Generation Utility
Generates an Ed25519 keypair for the Oracle vault.
"""

from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def main():
    vault = Path.home() / ".mirrornode" / "oracle" / "keys"
    vault.mkdir(parents=True, exist_ok=True)

    priv_path = vault / "oracle_ed25519_private.pem"
    pub_path = vault / "oracle_ed25519_public.pem"

    if priv_path.exists() or pub_path.exists():
        print("Keys already exist. No changes made.")
        print(f"Vault: {vault}")
        return

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_bytes)
    pub_path.write_bytes(pub_bytes)

    print("Ed25519 keypair generated.")
    print(f"Private key: {priv_path}")
    print(f"Public key : {pub_path}")

if __name__ == "__main__":
    main()

