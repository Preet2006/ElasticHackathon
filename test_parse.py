import re

# Simulate the context we're getting
context = '''=== Target: api_service.py ===
import os
import requests

def connect_to_payment_gateway():
    print("[*] Connecting to Stripe Payment Gateway...")
    
    # VULNERABILITY: Hardcoded Secrets
    api_key = "sk_live_51Mz...SECRET_KEY_HERE"
    admin_token = "ghp_1234567890abcdefghijklmn"
    db_password = "SuperSecretPassword123!"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Admin-Token": admin_token
    }
    
    try:
        print(f"DEBUG: Authenticating with key ending in ...{api_key[-4:]}")
        print("Connection successful (Simulated)")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    connect_to_payment_gateway()
'''

# Test the regex parsing
pattern = r'===\s*(Context|Target):\s*(.+?)\s*===\s*\n'
parts = re.split(pattern, context)
print(f'Number of parts: {len(parts)}')
for i, part in enumerate(parts):
    content = part[:100] if len(part) > 100 else part
    print(f'Part {i}: {content!r}')
print()
print("Extracted files:")
i = 0
if parts and not parts[0].strip():
    i = 1
elif parts and not re.match(r'(Context|Target)', parts[0]):
    i = 1
    
while i + 2 < len(parts):
    header_type = parts[i]
    file_path = parts[i + 1].strip()
    content = parts[i + 2].strip()
    print(f"  {header_type}: {file_path} = {len(content)} chars")
    print(f"    First 100 chars: {content[:100]!r}")
    i += 3
