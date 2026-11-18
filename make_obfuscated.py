#!/usr/bin/env python3
import base64

# Name of your working, un-obfuscated script file
source_file = "bot_clean.py"
output_file = "bot.py"

# Read raw bytes and encode to base64 (automatically handles correct padding)
with open(source_file, "rb") as f:
    encoded_data = base64.b64encode(f.read())

# Generate the wrapper script
wrapper_code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import sys

_0x_payload = {encoded_data!r}

try:
    print("[System] Loading obfuscated module...", flush=True)
    exec(base64.b64decode(_0x_payload), globals())
except Exception as _err:
    print(f"[Fatal Error] Failed to execute module: {{_err}}", file=sys.stderr)
    sys.exit(1)
"""

with open(output_file, "w") as f:
    f.write(wrapper_code)

print(f"Successfully generated obfuscated wrapper at '{output_file}'!")