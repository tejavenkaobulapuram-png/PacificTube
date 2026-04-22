"""Get actual video file sizes from Azure Blob Storage"""
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

# Get Azure credentials
storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
sas_token = os.getenv('AZURE_STORAGE_SAS_TOKEN')
account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')

# Connect to blob storage
if account_key:
    account_url = f"https://{storage_account}.blob.core.windows.net"
    blob_service_client = BlobServiceClient(account_url=account_url, credential=account_key)
elif sas_token:
    account_url = f"https://{storage_account}.blob.core.windows.net?{sas_token}"
    blob_service_client = BlobServiceClient(account_url=account_url)
else:
    print("❌ No Azure credentials found")
    exit(1)

# Get container
container_name = "videos"
container_client = blob_service_client.get_container_client(container_name)

print("\n📹 Video Files in Azure Blob Storage:\n")
print(f"{'#':<4} {'Size (MB)':<12} {'Size (GB)':<12} {'File Name'}")
print("=" * 100)

total_size_bytes = 0
video_count = 0
video_sizes = []

for blob in container_client.list_blobs():
    if blob.name.endswith('.mp4'):
        video_count += 1
        size_bytes = blob.size
        size_mb = size_bytes / (1024 * 1024)
        size_gb = size_bytes / (1024 * 1024 * 1024)
        total_size_bytes += size_bytes
        video_sizes.append((blob.name, size_mb))
        
        print(f"{video_count:<4} {size_mb:<12.2f} {size_gb:<12.3f} {blob.name}")

# Calculate statistics
total_mb = total_size_bytes / (1024 * 1024)
total_gb = total_size_bytes / (1024 * 1024 * 1024)
avg_mb = total_mb / video_count if video_count > 0 else 0

print("=" * 100)
print(f"\n📊 Summary:")
print(f"   Total videos: {video_count}")
print(f"   Total size: {total_mb:.2f} MB ({total_gb:.3f} GB)")
print(f"   Average size: {avg_mb:.2f} MB per video")
print(f"   Smallest: {min(video_sizes, key=lambda x: x[1])[1]:.2f} MB - {min(video_sizes, key=lambda x: x[1])[0]}")
print(f"   Largest: {max(video_sizes, key=lambda x: x[1])[1]:.2f} MB - {max(video_sizes, key=lambda x: x[1])[0]}")

# Calculate cost projections
print(f"\n💰 Storage Costs:")
print(f"   Current: ¥{total_gb * 2.50:.2f}/month")
print(f"   At 100 videos (same avg): ¥{(100 * avg_mb / 1024) * 2.50:.2f}/month")
