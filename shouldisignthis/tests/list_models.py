import os
import sys
from google.genai import Client

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shouldisignthis.config import configure_logging

configure_logging()

try:
    client = Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    print("Listing models...")
    for m in client.models.list():
        print(f"- {m.name}")
        # print(f"  Methods: {m.supported_generation_methods}") 
except Exception as e:
    print(f"Error listing models: {e}")
