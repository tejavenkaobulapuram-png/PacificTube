"""List available subtitle files"""
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

STORAGE_ACCOUNT = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
SAS_TOKEN = os.getenv('AZURE_STORAGE_SAS_TOKEN')

account_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net?{SAS_TOKEN}"
client = BlobServiceClient(account_url=account_url)
container = client.get_container_client('videos')

print("\n📁 Japanese subtitle files (.ja.vtt):")
print("="*60)

ja_files = [blob.name for blob in container.list_blobs() if '.ja.vtt' in blob.name]

for i, filename in enumerate(ja_files, 1):
    print(f"{i}. {filename}")

print(f"\n📊 Total: {len(ja_files)} files")
print("="*60)
