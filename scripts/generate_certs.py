import os
import sys
import subprocess
import datetime

# 1. Ensure the 'cryptography' library is installed for generating X509 certificates
try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print("[*] 'cryptography' library not found. Installing dynamically via pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

# Certs destination directory in the workspace root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_DIR = os.path.join(ROOT_DIR, "certs")
os.makedirs(CERT_DIR, exist_ok=True)

def generate_ca():
    print("[*] Generating Root CA Certificate and Key...")
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NEXUS-SIEM Security Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "NEXUS-SIEM Root CA"),
    ])
    
    ca_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        ca_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650) # 10 years validity
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(ca_key, hashes.SHA256())
    
    # Save CA private key
    with open(os.path.join(CERT_DIR, "ca.key"), "wb") as f:
        f.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    # Save CA cert
    with open(os.path.join(CERT_DIR, "ca.crt"), "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
        
    return ca_cert, ca_key

def generate_server_cert(ca_cert, ca_key):
    print("[*] Generating Server Certificate and Key (HTTPS)...")
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NEXUS-SIEM Systems"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    # Add localhost and 127.0.0.1 Subject Alternative Names (SANs)
    alt_names = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(datetime.ip_address("127.0.0.1"))
    ])
    
    server_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        server_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365) # 1 year validity
    ).add_extension(
        alt_names, critical=False,
    ).sign(ca_key, hashes.SHA256())
    
    # Save Server key
    with open(os.path.join(CERT_DIR, "server.key"), "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    # Save Server cert
    with open(os.path.join(CERT_DIR, "server.crt"), "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))

def generate_client_cert(ca_cert, ca_key):
    print("[*] Generating Agent Client Certificate and Key (mTLS authentication)...")
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NEXUS-SIEM Shipper Agents"),
        x509.NameAttribute(NameOID.COMMON_NAME, "nexus-shipper-agent-01"),
    ])
    
    client_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        client_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365) # 1 year validity
    ).sign(ca_key, hashes.SHA256())
    
    # Save Client key
    with open(os.path.join(CERT_DIR, "client.key"), "wb") as f:
        f.write(client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    # Save Client cert
    with open(os.path.join(CERT_DIR, "client.crt"), "wb") as f:
        f.write(client_cert.public_bytes(serialization.Encoding.PEM))

if __name__ == "__main__":
    import datetime
    # We import ipaddress here to avoid collision with standard imports
    import ipaddress
    datetime.ip_address = ipaddress.ip_address
    
    print("[*] Starting NEXUS-SIEM PKI Certificate Generation...")
    ca_cert, ca_key = generate_ca()
    generate_server_cert(ca_cert, ca_key)
    generate_client_cert(ca_cert, ca_key)
    print(f"[+] All certs successfully generated in: {CERT_DIR}")
