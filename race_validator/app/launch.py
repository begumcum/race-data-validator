"""Entry point for the `race-validator` command.

Starts the Streamlit app. Also handles --version.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # --version: print and exit before importing streamlit (slow import)
    if len(sys.argv) > 1 and sys.argv[1] in {"--version", "-v"}:
        from race_validator.version import CONTRACT_VERSION, LIBRARY_VERSION
        print(f"race-validator v{LIBRARY_VERSION} (contract v{CONTRACT_VERSION})")
        return

    # Locate the streamlit script inside the installed package
    import race_validator.app
    app_dir = Path(race_validator.app.__file__).parent
    script = app_dir / "streamlit_app.py"

    # Hand off to streamlit CLI
    from streamlit.web.cli import main as streamlit_main
    sys.argv = ["streamlit", "run", str(script)]
    sys.exit(streamlit_main())


if __name__ == "__main__":
    main()
