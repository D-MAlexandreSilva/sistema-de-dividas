from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1
import base64

with open("private_key.pem", "rb") as f:
    pem = f.read()

chave = load_pem_private_key(pem, password=None)

raw = chave.private_numbers().private_value.to_bytes(32, byteorder='big')

print(base64.urlsafe_b64encode(raw).rstrip(b"=").decode())