import requests
import base64
import hmac
import hashlib
import time
import struct

def generate_totp(secret):
    # Generate TOTP using HMAC-SHA-512
    t = int(time.time()) // 30
    msg = struct.pack(">Q", t)
    h = hmac.new(secret.encode(), msg, hashlib.sha512).digest()
    o = h[-1] & 0x0F
    token = (struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % 10000000000
    return f"{token:010d}"

def main():
    # Replace with your details
    github_url = "https://gist.github.com/mskaushik1709/a39c98d50c2555ebf22a62f41f3b164a"
    contact_email = "mskaushik17092002@gmail.com"
    solution_language = "python"

    # Generate TOTP
    shared_secret = f"{contact_email}HENNGECHALLENGE003"
    totp_password = generate_totp(shared_secret)

    # Construct JSON
    json_data = {
        "github_url": github_url,
        "contact_email": contact_email,
        "solution_language": solution_language
    }

    # Send POST request
    auth_string = f"{contact_email}:{totp_password}"
    auth_bytes = auth_string.encode("ascii")
    auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }

    response = requests.post(
        "https://api.challenge.hennge.com/challenges/003",
        json=json_data,
        headers=headers
    )

    print(response.status_code)
    print(response.text)

if __name__ == "__main__":
    main()