from pinecone import Pinecone
from dotenv import load_dotenv
import os

load_dotenv(override=True)
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX = os.getenv('PINECONE_INDEX')

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

print('Deleting all existing records...')
index.delete(delete_all=True)
print('✅ All records deleted successfully!')
