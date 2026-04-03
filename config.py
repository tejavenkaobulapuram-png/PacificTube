"""
Azure Blob Storage Configuration
"""

import os

# Azure Blob Storage Settings
STORAGE_ACCOUNT_NAME = "pacifictubestorage"
CONTAINER_NAME = "videos"

# SAS Token (expires 2027-03-19) - generates from Azure CLI
SAS_TOKEN = "se=2027-03-19T23%3A59%3A59Z&sp=racwl&spr=https&sv=2026-02-06&sr=c&sig=MMGxV2R4Bndc%2B%2BJlyJ7HGGDlV0h45IA8z67WIdkT0dk%3D"

# Storage Account Key (for generating short-lived SAS tokens)
# IMPORTANT: Set this in .env file or Azure App Service Configuration
# Do NOT commit actual keys to git!
STORAGE_ACCOUNT_KEY = os.environ.get('AZURE_STORAGE_ACCOUNT_KEY', '')

# Optional: Folder path inside container (leave empty to show all folders in sidebar)
FOLDER_PATH = ""  # Empty = show folder tree navigation

# Construct Blob URLs
BLOB_SERVICE_URL = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
CONTAINER_URL = f"{BLOB_SERVICE_URL}/{CONTAINER_NAME}"

# Flask Settings
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
HOST = "0.0.0.0"
PORT = int(os.environ.get('PORT', 5000))

# Cloud Storage Settings (for production/container deployment)
USE_CLOUD_STORAGE = os.environ.get('USE_CLOUD_STORAGE', 'False').lower() == 'true'

# Azure Table Storage (for view tracking)
# Can use either connection string or SAS token
TABLE_CONNECTION_STRING = os.environ.get('AZURE_TABLE_CONNECTION_STRING', '')
TABLE_SAS_TOKEN = os.environ.get('AZURE_TABLE_SAS_TOKEN', SAS_TOKEN)  # Reuse blob SAS if not specified

# Thumbnail Storage Container
THUMBNAIL_CONTAINER = "thumbnails"
