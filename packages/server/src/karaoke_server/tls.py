"""The server's own TLS certificate, made on first start and pinned by every node.

Nodes never trust a certificate authority here: when they enrol they learn the SHA-256 of the
certificate (over a channel the operator trusts: the token is typed or pasted from the server's
console) and from then on accept only that one. That works the same on the LAN and over
Tailscale, and needs no domain name.
"""

import datetime
import hashlib
import ipaddress
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CERT = "server.crt"
KEY = "server.key"


def _names(extra: tuple[str, ...]) -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = []
    seen: set[str] = set()
    for name in ("localhost", socket.gethostname(), "127.0.0.1", "::1", *extra):
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(name)))
        except ValueError:
            names.append(x509.DNSName(name))
    return names


def ensure_certificate(folder: Path, names: tuple[str, ...] = ()) -> tuple[Path, Path]:
    """The certificate and key paths, made if missing (ECDSA P-256, valid for ten years)."""
    folder.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = folder / CERT, folder / KEY
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "karaoke-server")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(_names(names)), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def fingerprint(cert_path: Path) -> str:
    """SHA-256 of the certificate in DER, in lower-case hex: what nodes pin."""
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    return hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
