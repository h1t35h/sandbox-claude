#!/usr/bin/env python3
"""Test script to verify the clean command properly removes exited containers."""

import subprocess
import sys
import time


def run_command(cmd):
    """Run a command and return output."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result


def main():
    print("Testing sandbox-claude clean --all command\n")

    # List current containers
    print("1. Listing current containers:")
    run_command("sandbox-claude list --all")

    # Create a test container
    print("\n2. Creating a test container:")
    result = run_command("sandbox-claude new -p test-project -f test-feature -d")
    if result.returncode != 0:
        print("Failed to create test container")
        sys.exit(1)

    time.sleep(2)

    # List containers to see it running
    print("\n3. Listing containers (should show running):")
    run_command("sandbox-claude list --all")

    # Stop the container
    print("\n4. Stopping the test container:")
    run_command("sandbox-claude stop -p test-project")

    time.sleep(2)

    # List containers to see it stopped/exited
    print("\n5. Listing containers (should show exited/stopped):")
    run_command("sandbox-claude list --all")

    # Clean all containers
    print("\n6. Cleaning all stopped/exited containers:")
    run_command("sandbox-claude clean --all --force")

    # List containers to verify they're removed
    print("\n7. Listing containers (should be empty or only running containers):")
    run_command("sandbox-claude list --all")

    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
