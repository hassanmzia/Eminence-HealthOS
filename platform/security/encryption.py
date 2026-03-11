"""
PHI encryption utilities for HIPAA compliance.

Provides AES-256 field-level encryption for Protected Health Information.
"""

import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger("healthos.security.encryption")


class PHIEncryptor:
    """AES-256-GCM encryption for PHI fields."""

    def __init__(self, key: Optional[str] = None):
        if key is None:
            from platform.config.settings import get_settings
            key = get_settings().phi_encryption_key

        # Derive a 32-byte key via SHA-256
        self._key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a base64-encoded ciphertext."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        raw = base64.b64decode(encrypted)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


class AuditHashChain:
    """SHA-256 hash chain for tamper-evident audit logs."""

    @staticmethod
    def compute_hash(
        event_data: str,
        previous_hash: str = "",
    ) -> str:
        """Compute the next hash in the chain."""
        content = f"{previous_hash}|{event_data}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_chain(entries: list[dict]) -> bool:
        """Verify integrity of an audit log chain."""
        for i, entry in enumerate(entries):
            prev_hash = entries[i - 1]["hash"] if i > 0 else ""
            expected = AuditHashChain.compute_hash(
                entry["event_data"], prev_hash
            )
            if entry["hash"] != expected:
                logger.warning("Hash chain broken at entry %d", i)
                return False
        return True
