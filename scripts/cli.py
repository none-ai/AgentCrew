#!/usr/bin/env python3
"""
Compatibility wrapper for the packaged AgentCrew CLI.
"""

from AgentCrew.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
