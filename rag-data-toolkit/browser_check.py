from __future__ import annotations

from utils.browser_utils import find_system_chrome


def main() -> int:
    path = find_system_chrome()
    if path:
        print(f"SYSTEM_CHROME_FOUND={path}")
        return 0
    print("SYSTEM_CHROME_NOT_FOUND")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
