#!/usr/bin/env python3
"""Embed the WiiM logo PNG as base64 in constants.py."""

import base64
from pathlib import Path

# Read the PNG file
logo_file = Path("wiim-logo.png")
if not logo_file.exists():
    print(f"❌ Logo file not found: {logo_file}")
    exit(1)

logo_bytes = logo_file.read_bytes()
print(f"📦 Logo file size: {len(logo_bytes):,} bytes ({len(logo_bytes)/1024:.2f} KB)")

# Encode to base64
base64_encoded = base64.b64encode(logo_bytes).decode('ascii')
print(f"📦 Base64 size: {len(base64_encoded):,} bytes ({len(base64_encoded)/1024:.2f} KB)")

# Create the constant
print("\n" + "="*80)
print("Add this to pywiim/api/constants.py:")
print("="*80)
print()
print("# Embedded PyWiim logo (PNG format)")
print("# Used as fallback when no cover art is available")
print(f"# Size: {len(logo_bytes)} bytes ({len(logo_bytes)/1024:.2f} KB)")
print("EMBEDDED_LOGO_BASE64 = (")

# Split into 80-char lines for readability
chunk_size = 80
for i in range(0, len(base64_encoded), chunk_size):
    chunk = base64_encoded[i:i+chunk_size]
    print(f'    "{chunk}"')

print(")")
print()
print("="*80)

# Save to file for easy copy/paste
output_file = Path("embedded-logo-constant.txt")
with open(output_file, "w") as f:
    f.write("# Embedded PyWiim logo (PNG format)\n")
    f.write("# Used as fallback when no cover art is available\n")
    f.write(f"# Size: {len(logo_bytes)} bytes ({len(logo_bytes)/1024:.2f} KB)\n")
    f.write("EMBEDDED_LOGO_BASE64 = (\n")
    for i in range(0, len(base64_encoded), chunk_size):
        chunk = base64_encoded[i:i+chunk_size]
        f.write(f'    "{chunk}"\n')
    f.write(")\n")

print(f"✅ Saved to: {output_file}")

