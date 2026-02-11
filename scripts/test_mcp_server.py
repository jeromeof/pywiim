#!/usr/bin/env python3
"""End-to-end test of the MCP server.

Spawns wiim-mcp, sends tool calls, and prints results. Uses config with
discovery_disabled and 192.168.1.x devices. Device tools (wiim_status, etc.)
will fail if no real device exists, but the flow is still verified.

Usage:
  python scripts/test_mcp_server.py

With real device:
  WIIM_TEST_DEVICE=192.168.1.115 python scripts/test_mcp_server.py
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile


def main() -> None:
    test_device = os.environ.get("WIIM_TEST_DEVICE")
    device_ip = test_device or "192.168.1.115"
    # Short timeout so failures are fast when no device
    timeout = 2.0 if not test_device else 5.0

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "default_device": device_ip,
                "named_devices": {
                    "Living Room": device_ip,
                    "Bedroom": "192.168.1.116",
                    "Kitchen": "192.168.1.68",
                },
                "discovery_disabled": True,
                "timeout": timeout,
            },
            f,
            indent=2,
        )
        cfg_path = f.name

    env = os.environ.copy()
    env["WIIM_CONFIG_FILE"] = cfg_path

    proc = subprocess.Popen(
        ["wiim-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    try:

        def send(method: str, params: dict | None = None, id_: int = 1) -> None:
            msg: dict = {"jsonrpc": "2.0", "id": id_, "method": method}
            if params:
                msg["params"] = params
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()

        def call_tool(name: str, args: dict | None = None) -> dict:
            send("tools/call", {"name": name, "arguments": args or {}}, id_=99)
            return json.loads(proc.stdout.readline())

        def read() -> dict:
            return json.loads(proc.stdout.readline())

        # 1. Initialize
        send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "e2e-test", "version": "1.0"},
            },
        )
        r = read()
        name = r.get("result", {}).get("serverInfo", {}).get("name", "?")
        print(f"1. Initialize: {name} OK")

        # 2. Notifications/initialized (required after initialize)
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # 3. List tools
        send("tools/list", id_=2)
        r = read()
        tools = r.get("result", {}).get("tools", [])
        print("2. tools/list:", len(tools), "tools")
        print("   ", ", ".join(t["name"] for t in tools[:8]), "...")

        # 4. wiim_discover (no device needed)
        r = call_tool("wiim_discover")
        text = r.get("result", {}).get("content", [{}])[0].get("text", "")
        print("3. wiim_discover:")
        for line in text.splitlines():
            print(f"   {line}")

        # 5. Device tools (needs real device; skip if no WIIM_TEST_DEVICE to avoid slow timeouts)
        if test_device:
            r = call_tool("wiim_status", {"device_ip": device_ip})
            text = r.get("result", {}).get("content", [{}])[0].get("text", "")
            print("4. wiim_status:")
            print(f"   {text[:300]}{'...' if len(text) > 300 else ''}")

            r = call_tool("wiim_sources", {"device_ip": device_ip})
            text = r.get("result", {}).get("content", [{}])[0].get("text", "")
            print("5. wiim_sources:")
            print(f"   {text[:200]}{'...' if len(text) > 200 else ''}")

            r = call_tool("wiim_volume", {"device_ip": device_ip})
            text = r.get("result", {}).get("content", [{}])[0].get("text", "")
            print("6. wiim_volume (get):")
            print(f"   {text}")
        else:
            print("4-6. Skipping device tools (set WIIM_TEST_DEVICE=192.168.1.115 to test)")

        print("\nDone. All tool calls completed.")
    finally:
        proc.terminate()
        proc.wait(timeout=2)
        os.unlink(cfg_path)


if __name__ == "__main__":
    main()
