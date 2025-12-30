"""
Global Configuration
====================
This module defines global configuration variables for the Lemma Client.
By centralizing configuration here, we make it easy to maintain and update
project-wide settings like the program name.
"""

# Program name - used throughout the toolkit for filenames, commands, etc.
PROG_NAME = "lemma"

# Use PID manager for service management
USE_PID_MANAGER = True

# Service names
SERVICE_NAME_SYSTEMD = "lemma-client.service"
SERVICE_NAME_LAUNCHD = "com.lemma.client.plist"
LAUNCHD_LABEL = "com.lemma.client"

# Directory and file names
LEMMA_DIR_NAME = ".lemma"  # Home directory name for client data
LOG_FILENAME = f"{PROG_NAME}.log"
STDOUT_LOG_FILENAME = f"{PROG_NAME}-stdout.log"

# Service ready marker
SERVICE_STARTED_MARKER = "Remote Client Service is starting right now..."
SERVICE_READY_MARKER = "Remote Client Service started successfully"

LEMMA_CONFIG = {
    "debug": False,
}