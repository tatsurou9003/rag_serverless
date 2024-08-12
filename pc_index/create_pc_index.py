from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import os
from dotenv import load_dotenv

load_dotenv()
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
index_name = os.environ.get("PINECONE_INDEX_NAME")

# pineconeのindexを作成
pc = Pinecone(api_key=pinecone_api_key)
pc.create_index(
    name=index_name,
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)
index_description = pc.describe_index(index_name)
endpoint = index_description.get("host")

print(f"Index endpoint: {endpoint}")
