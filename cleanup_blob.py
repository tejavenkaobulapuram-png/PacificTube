#!/usr/bin/env python3
"""
Clean up duplicate and unnecessary files from Azure Blob Storage
"""

import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure Storage configuration
storage_account = 'pacifictubesa'
blob_sas = os.getenv('AZURE_STORAGE_BLOB_SAS_TOKEN')
container_name = 'videos'

# Create blob service client
blob_service_client = BlobServiceClient(
    account_url=f"https://{storage_account}.blob.core.windows.net",
    credential=blob_sas
)
container_client = blob_service_client.get_container_client(container_name)

print("="*70)
print("Blob Storage Cleanup Tool")
print("="*70)
print()

# List all blobs
print("📋 Scanning blob storage...")
all_blobs = list(container_client.list_blobs())

# Find chapter files
chapter_blobs = [blob for blob in all_blobs if blob.name.endswith('.chapters.json')]

print(f"Found {len(chapter_blobs)} chapter files in blob storage\n")

# Group by filename to find duplicates
from collections import defaultdict
blob_groups = defaultdict(list)

for blob in chapter_blobs:
    filename = os.path.basename(blob.name)
    blob_groups[filename].append(blob.name)

# Find duplicates (files that appear more than once)
duplicates_to_remove = []

print("🔍 Checking for duplicates...\n")
for filename, paths in blob_groups.items():
    if len(paths) > 1:
        print(f"Found duplicate: {filename}")
        for path in paths:
            print(f"   - {path}")
        
        # Keep only the one in a subfolder (03_定例会議/Recordings/)
        # Remove the one at root level
        for path in paths:
            if '/' not in path or path.count('/') == 0:
                # Root level file - mark for deletion
                duplicates_to_remove.append(path)
                print(f"   ❌ Will remove: {path}")
        print()

if not duplicates_to_remove:
    print("✅ No unnecessary files found!")
else:
    print(f"\n⚠️  Found {len(duplicates_to_remove)} unnecessary files to remove:")
    for blob_path in duplicates_to_remove:
        print(f"   - {blob_path}")
    
    confirmation = input(f"\nRemove these {len(duplicates_to_remove)} files? (yes/no): ").strip().lower()
    
    if confirmation == 'yes':
        print("\n🗑️  Removing unnecessary files...\n")
        for blob_path in duplicates_to_remove:
            try:
                blob_client = container_client.get_blob_client(blob_path)
                blob_client.delete_blob()
                print(f"   ✅ Deleted: {blob_path}")
            except Exception as e:
                print(f"   ❌ Failed to delete {blob_path}: {e}")
        
        print(f"\n✅ Cleanup complete! Removed {len(duplicates_to_remove)} files")
    else:
        print("\n❌ Cleanup cancelled")

print("\n" + "="*70)
