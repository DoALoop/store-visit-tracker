import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import aiplatform, bigquery
from google.cloud.aiplatform_v1.types import HarmCategory, SafetySetting
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
import vertexai
import json
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables from a .env file (good practice)
load_dotenv()

# --- Configuration ---
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION", "us-central1") # Default location
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "store_visits")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "store_visits")

if not GOOGLE_PROJECT_ID:
    raise ValueError("GOOGLE_PROJECT_ID environment variable not set.")

# The fully-qualified BigQuery table ID
TABLE_ID = f"{GOOGLE_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"

# Initialize Vertex AI
vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)

# Initialize BigQuery Client
bigquery_client = bigquery.Client(project=GOOGLE_PROJECT_ID)

# --- FastAPI App Setup ---
app = FastAPI(
    title="Store Visit Tracker API",
    description="API for processing handwritten store visit notes.",
)

# --- BigQuery Setup Function (Runs on Startup) ---
def setup_bigquery():
    """Checks for dataset and table, creates them if they don't exist."""
    
    # --- Create Dataset if not exists ---
    dataset_id = f"{GOOGLE_PROJECT_ID}.{BIGQUERY_DATASET}"
    try:
        bigquery_client.get_dataset(dataset_id)  # Make an API request.
        print(f"Dataset {dataset_id} already exists.")
    except Exception:
        print(f"Dataset {dataset_id} not found, creating...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = GOOGLE_LOCATION
        dataset = bigquery_client.create_dataset(dataset, timeout=30)  # Make an API request.
        print(f"Created dataset {dataset.project}.{dataset.dataset_id}")

    # --- Create Table if not exists ---
    try:
        bigquery_client.get_table(TABLE_ID)  # Make an API request.
        print(f"Table {TABLE_ID} already exists.")
    except Exception:
        print(f"Table {TABLE_ID} not found, creating...")
        
        # Define the schema based on our AI output
        schema = [
            bigquery.SchemaField("visit_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("store_notes", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("store_rating", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("good", "STRING", mode="REPEATED"),
            bigquery.SchemaField("top_3_fixes", "STRING", mode="REPEATED"),
            bigquery.SchemaField("needs_from_me", "STRING", mode="REPEATED"),
        ]
        
        table = bigquery.Table(TABLE_ID, schema=schema)
        table = bigquery_client.create_table(table)  # Make an API request.
        print(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")

@app.on_event("startup")
def on_startup():
    """Run the BigQuery setup on application startup."""
    print("Running BigQuery setup...")
    setup_bigquery()
    print("BigQuery setup complete.")

# --- CORS Middleware ---
# This allows your frontend (running on a different domain/port)
# to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models (Data Validation) ---
class ImageUploadRequest(BaseModel):
    """Defines the expected data structure for an image upload."""
    mime_type: str
    image_data: str  # This will be the base64-encoded string

class NoteSchema(BaseModel):
    """Defines the JSON structure we expect from the AI."""
    store_notes: str
    store_rating: str
    good: list[str]
    top_3_fixes: list[str]
    needs_from_me: list[str]

# --- AI Model Setup ---
# Define the JSON schema for the model's output
response_schema = {
    "type": "OBJECT",
    "properties": {
        "store_notes": {"type": "STRING"},
        "store_rating": {"type": "STRING"},
        "good": {"type": "ARRAY", "items": {"type": "STRING"}},
        "top_3_fixes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "needs_from_me": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["store_notes", "store_rating", "good", "top_3_fixes", "needs_from_me"]
}

generation_config = GenerationConfig(
    response_mime_type="application/json",
    response_schema=response_schema,
)

# Set safety settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# System prompt for the AI
system_prompt = "You are an expert analyst processing handwritten store visit notes."
user_query = """
    Please analyze the attached image of handwritten notes from a store visit.
    Transcribe all the handwriting.
    From the transcribed text, extract the information according to the provided JSON schema.
    If you cannot find information for a field, use an empty string "" or an empty array [].

    For the store_rating field: Look for mentions of "Red", "Yellow", or "Green" in the notes.
    If the user wrote one of these ratings, extract it exactly (Red, Yellow, or Green).
    If no rating is mentioned, return "Not Rated".
"""

# Initialize the Generative Model
model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=[system_prompt],
    generation_config=generation_config,
    safety_settings=safety_settings
)

# --- API Endpoints ---
@app.get("/", summary="Health Check")
def read_root():
    """Simple health check endpoint."""
    return {"status": "Store Visit API is running"}

@app.post("/api/upload-visit", response_model=NoteSchema, summary="Analyze Handwritten Note")
async def upload_visit_notes(request: ImageUploadRequest):
    """
    Receives a base64-encoded image, sends it to Vertex AI for analysis,
    saves the result to BigQuery, and returns the structured JSON data.
    """
    try:
        # Create the image part for the model
        image_part = Part.from_data(
            data=request.image_data,
            mime_type=request.mime_type
        )

        # Create the text part
        text_part = Part.from_text(user_query)

        # Send the request to the model
        response = model.generate_content([text_part, image_part])

        # Extract the JSON text and parse it
        json_text = response.candidates[0].content.parts[0].text
        parsed_data = json.loads(json_text)

        # --- BIGQUERY INTEGRATION POINT ---
        
        # 1. Create a row to insert (add a visit_date, store_id, etc.):
        row_to_insert = {
            "visit_timestamp": datetime.now(timezone.utc).isoformat(),
            "store_notes": parsed_data["store_notes"],
            "store_rating": parsed_data["store_rating"],
            "good": parsed_data["good"],
            "top_3_fixes": parsed_data["top_3_fixes"],
            "needs_from_me": parsed_data["needs_from_me"]
        }
        
        # 2. Insert the row:
        print(f"Inserting row into {TABLE_ID}: {row_to_insert}")
        errors = bigquery_client.insert_rows_json(TABLE_ID, [row_to_insert])
        
        if errors:
            print(f"Error inserting to BigQuery: {errors}")
            # We'll still return the data to the user, but log the error
            # In production, you might want to handle this more gracefully
        else:
            print("Row successfully inserted into BigQuery.")
        
        # ------------------------------------

        # Return the parsed data to the frontend
        return parsed_data

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during analysis: {str(e)}"
        )

# --- Run the Server ---
if __name__ == "__main__":
    """
    This allows you to run the server directly using `python main.py`
    """
    print(f"Starting server... (Project: {GOOGLE_PROJECT_ID}, BQ Table: {TABLE_ID})")
    print("Go to http://127.0.0.1:8000/docs for API docs.")
    uvicorn.run(app, host="127.0.0.1", port=8000)