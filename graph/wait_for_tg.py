"""Health-check loop for TigerGraph."""

import os
import sys
import time

import requests

TG_HOST = os.getenv("TG_HOST", "tigergraph")
TG_PORT = os.getenv("TG_PORT", "9000")
TIMEOUT_SECONDS = int(os.getenv("TG_WAIT_TIMEOUT", "300"))


def wait_for_tigergraph(
    host: str = TG_HOST,
    port: str = TG_PORT,
    timeout: int = TIMEOUT_SECONDS,
) -> bool:
    """Block until TigerGraph is reachable or timeout."""
    url = f"http://{host}:{port}/echo"
    start = time.time()
    delay = 2

    print(f"Waiting for TigerGraph at {url} (timeout={timeout}s) …")

    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                elapsed = round(time.time() - start, 1)
                print(f"TigerGraph is ready ({elapsed}s)")
                return True
        except requests.ConnectionError:
            pass
        except requests.Timeout:
            pass

        time.sleep(delay)
        delay = min(delay * 1.5, 15)

    print("TigerGraph did not become ready within the timeout.")
    return False


if __name__ == "__main__":
    ok = wait_for_tigergraph()
    sys.exit(0 if ok else 1)
