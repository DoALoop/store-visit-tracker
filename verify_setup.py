import os
from google.cloud import bigquery
import vertexai
from dotenv import load_dotenv

# Load env vars
load_dotenv()

def verify():
    print("--- Verifying Google Cloud Setup ---")
    
    # 1. Check Project ID
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    if not project_id:
        print("❌ GOOGLE_PROJECT_ID not found in .env")
        return
    print(f"✅ Project ID found: {project_id}")

    # 2. Check Credentials
    cred_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_file:
        # Try to find the json file in current dir
        # We look for the specific file we saw in the file list or any likely candidate
        possible_files = [f for f in os.listdir('.') if f.endswith('.json') and 'store-visit-tracker' in f]
        if possible_files:
            cred_file = os.path.abspath(possible_files[0])
            # We set it for this process to test if it works
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_file
            print(f"⚠️  GOOGLE_APPLICATION_CREDENTIALS not set in .env.")
            print(f"   Found potential key file: {cred_file}")
            print(f"   Using it for this test...")
        else:
            print("❌ GOOGLE_APPLICATION_CREDENTIALS not set and no JSON key file found.")
            return
    else:
        print(f"✅ Credentials file set: {cred_file}")

    # 3. Test BigQuery
    try:
        client = bigquery.Client(project=project_id)
        # Just try to get the client project to verify auth
        print(f"   Authenticated as project: {client.project}")
        datasets = list(client.list_datasets())
        print(f"✅ BigQuery Connection Successful. Found {len(datasets)} datasets.")
    except Exception as e:
        print(f"❌ BigQuery Connection Failed: {e}")
        return

    # 4. Test Vertex AI
    try:
        vertexai.init(project=project_id, location=os.getenv("GOOGLE_LOCATION", "us-central1"))
        print("✅ Vertex AI Initialization Successful.")
    except Exception as e:
        print(f"❌ Vertex AI Initialization Failed: {e}")
        return

    print("\n🎉 Setup looks good! (Don't forget to add GOOGLE_APPLICATION_CREDENTIALS to your .env file)")

if __name__ == "__main__":
    verify()
