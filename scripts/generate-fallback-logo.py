#!/usr/bin/env python3
"""Generate a base64-encoded SVG logo for PyWiim cover art fallback."""

import base64

# Simple music note SVG icon (clean, modern design)
# Color scheme: Dark blue/purple gradient matching audio device aesthetics
svg_logo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <!-- Background -->
  <rect width="200" height="200" fill="#1a1a2e" rx="10"/>
  
  <!-- Gradient definition -->
  <defs>
    <linearGradient id="musicGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Music note icon -->
  <g transform="translate(60, 40)">
    <!-- Note stem -->
    <rect x="50" y="10" width="6" height="80" fill="url(#musicGradient)" rx="3"/>
    
    <!-- Note head (ellipse) -->
    <ellipse cx="43" cy="100" rx="18" ry="14" fill="url(#musicGradient)"/>
    
    <!-- Eighth note flag -->
    <path d="M 56 10 Q 75 15, 75 35 Q 75 45, 65 50 L 56 45 Z" fill="url(#musicGradient)"/>
  </g>
  
  <!-- "PyWiim" text -->
  <text x="100" y="160" font-family="Arial, sans-serif" font-size="20" font-weight="bold" 
        text-anchor="middle" fill="#ffffff" opacity="0.9">PyWiim</text>
</svg>"""

# Minimize SVG (remove unnecessary whitespace)
svg_minimized = " ".join(svg_logo.split())

# Encode to base64
svg_bytes = svg_minimized.encode("utf-8")
base64_encoded = base64.b64encode(svg_bytes).decode("ascii")

# Create data URI
data_uri = f"data:image/svg+xml;base64,{base64_encoded}"

print("=" * 80)
print("PyWiim Fallback Logo (Base64 Data URI)")
print("=" * 80)
print()
print("Size Information:")
print(f"  SVG size: {len(svg_bytes)} bytes")
print(f"  Base64 size: {len(base64_encoded)} bytes")
print(f"  Data URI size: {len(data_uri)} bytes")
print()
print("To use in constants.py:")
print("-" * 80)
print(f'DEFAULT_WIIM_LOGO_URL = "{data_uri}"')
print("-" * 80)
print()
print("Full Data URI:")
print(data_uri[:100] + "..." if len(data_uri) > 100 else data_uri)
print()

# Save to file for testing
output_file = "pywiim-fallback-logo.svg"
with open(output_file, "w") as f:
    f.write(svg_logo)
print(f"✅ SVG saved to: {output_file}")
print(f"   You can open this in a browser to preview the logo")
print()

# Also save the full data URI constant
constant_file = "pywiim-fallback-logo-constant.txt"
with open(constant_file, "w") as f:
    f.write(f"# PyWiim fallback logo (base64-encoded SVG)\n")
    f.write(f"# Size: {len(data_uri)} bytes\n")
    f.write(f'DEFAULT_WIIM_LOGO_URL = "{data_uri}"\n')
print(f"✅ Constant saved to: {constant_file}")
print(f"   Copy this into pywiim/api/constants.py (line 144)")
print()
print("=" * 80)
