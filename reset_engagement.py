"""
Reset all engagement data (likes, dislikes, comments, views) to zero
This script clears all data from Azure Table Storage for a fresh start
"""

from azure.data.tables import TableServiceClient
from azure.core.credentials import AzureSasCredential
from dotenv import load_dotenv
import os
import config

load_dotenv()

# Try connection string first, then SAS token
table_service = None

if config.TABLE_CONNECTION_STRING:
    print("🔑 Using connection string...")
    table_service = TableServiceClient.from_connection_string(config.TABLE_CONNECTION_STRING)
elif config.TABLE_SAS_TOKEN and config.STORAGE_ACCOUNT_NAME:
    print("🔑 Using SAS token...")
    account_url = f"https://{config.STORAGE_ACCOUNT_NAME}.table.core.windows.net"
    credential = AzureSasCredential(config.TABLE_SAS_TOKEN)
    table_service = TableServiceClient(endpoint=account_url, credential=credential)
else:
    print("❌ Error: No valid Azure Table Storage credentials found")
    exit(1)

tables_to_clear = ['videolikes', 'videocomments', 'views']

for table_name in tables_to_clear:
    print(f"\n🗑️ Clearing table: {table_name}")
    
    try:
        table_client = table_service.get_table_client(table_name)
        
        # Get all entities
        entities = list(table_client.list_entities())
        count = len(entities)
        
        if count == 0:
            print(f"   ✅ Table is already empty")
            continue
        
        print(f"   📊 Found {count} entries to delete...")
        
        # Delete each entity
        deleted = 0
        for entity in entities:
            try:
                table_client.delete_entity(
                    partition_key=entity['PartitionKey'],
                    row_key=entity['RowKey']
                )
                deleted += 1
                if deleted % 10 == 0:
                    print(f"   Deleted {deleted}/{count}...")
            except Exception as e:
                print(f"   ⚠️ Error deleting entity: {e}")
        
        print(f"   ✅ Deleted {deleted} entries from {table_name}")
        
    except Exception as e:
        print(f"   ❌ Error with table {table_name}: {e}")

print("\n" + "="*50)
print("🎉 RESET COMPLETE! All engagement data cleared to zero.")
print("   - Likes: 0")
print("   - Dislikes: 0") 
print("   - Comments: 0")
print("   - Views: 0")
print("="*50)
