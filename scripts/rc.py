#!/usr/bin/env python3
"""
rc.py - Regularize Consultoria CLI
-----------------------------------
Command-line interface for RC Gestor de Clientes.

Usage:
    python scripts/rc.py <command> [--arg1=val1] [--arg2=val2]

Examples:
    # List available commands
    python scripts/rc.py --list

    # Get help for a command
    python scripts/rc.py --help theme:switch

    # Execute a command
    python scripts/rc.py upload:folder --local_dir=/docs --org_id=123 --client_id=456

    # Search clients
    python scripts/rc.py client:search --query="Acme Corp"

    # List trash
    python scripts/rc.py trash:list --org_id=123

Note: This is an optional CLI tool. The GUI (app_gui.py) remains the primary interface.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application import commands


def parse_args() -> tuple[str, Dict[str, Any]]:
    """
    Parse command-line arguments.

    Returns:
        (command_name, kwargs_dict)
    """
    parser = argparse.ArgumentParser(
        description="RC Gestor de Clientes CLI",
        epilog="For command-specific help: rc.py --help <command>",
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute (e.g., upload:folder, theme:switch)",
    )

    parser.add_argument(
        "--list", action="store_true", help="List all available commands"
    )

    parser.add_argument(
        "--help-command", metavar="COMMAND", help="Show help for a specific command"
    )

    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    # Parse known args (command + flags)
    args, unknown = parser.parse_known_args()

    # Parse unknown args as --key=value kwargs
    kwargs = {}
    for arg in unknown:
        if arg.startswith("--"):
            if "=" in arg:
                key, value = arg[2:].split("=", 1)
                # Try to parse as JSON (for lists, dicts, etc.)
                try:
                    kwargs[key] = json.loads(value)
                except json.JSONDecodeError:
                    # Fallback: treat as string
                    kwargs[key] = value
            else:
                # Flag without value (treat as True)
                kwargs[arg[2:]] = True

    return args, kwargs


def list_commands_cli() -> None:
    """Print list of available commands."""
    cmd_list = commands.list_commands()

    print("Available commands:")
    print()

    for name, help_text in sorted(cmd_list.items()):
        print(f"  {name:20s}  {help_text}")

    print()
    print(f"Total: {len(cmd_list)} commands")


def show_command_help(command_name: str) -> None:
    """Show detailed help for a command."""
    info = commands.get_command_info(command_name)

    if info is None:
        print(f"Error: Command '{command_name}' not found")
        print()
        list_commands_cli()
        sys.exit(1)

    print(f"Command: {info['name']}")
    print(f"Help: {info['help']}")
    print(f"Function: {info['func']}")

    if info["defaults"]:
        print()
        print("Default arguments:")
        for key, value in info["defaults"].items():
            print(f"  --{key}={json.dumps(value)}")

    print()
    print("Usage:")
    print(f"  python scripts/rc.py {info['name']} [--arg1=val1] [--arg2=val2]")


def main() -> int:
    args, kwargs = parse_args()

    # Handle --list
    if args.list:
        list_commands_cli()
        return 0

    # Handle --help-command
    if args.help_command:
        show_command_help(args.help_command)
        return 0

    # Validate command provided
    if not args.command:
        print("Error: No command specified")
        print()
        list_commands_cli()
        return 1

    # Execute command
    try:
        result = commands.run(args.command, **kwargs)

        if args.json:
            # JSON output
            print(
                json.dumps(
                    {"success": True, "command": args.command, "result": result},
                    indent=2,
                    default=str,
                )
            )
        else:
            # Human-readable output
            print(f"✅ Command '{args.command}' executed successfully")

            if result is not None:
                print()
                print("Result:")
                if isinstance(result, (dict, list)):
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(result)

        return 0

    except KeyError as e:
        print(f"❌ Error: {e}")
        print()
        list_commands_cli()
        return 1

    except Exception as e:
        print(f"❌ Command failed: {e}")

        if args.json:
            print(
                json.dumps(
                    {"success": False, "command": args.command, "error": str(e)},
                    indent=2,
                )
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
