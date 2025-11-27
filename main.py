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
    """Checks for dataset and table. Assumes table already exists with correct schema."""

    # --- Check Dataset exists ---
    dataset_id = f"{GOOGLE_PROJECT_ID}.{BIGQUERY_DATASET}"
    try:
        bigquery_client.get_dataset(dataset_id)  # Make an API request.
        print(f"Dataset {dataset_id} exists.")
    except Exception as e:
        print(f"Error: Dataset {dataset_id} not found: {e}")
        print("Please create the dataset in BigQuery first.")
        raise

    # --- Check Table exists ---
    try:
        bigquery_client.get_table(TABLE_ID)  # Make an API request.
        print(f"Table {TABLE_ID} exists and ready to use.")
    except Exception as e:
        print(f"Error: Table {TABLE_ID} not found: {e}")
        print("Please ensure your BigQuery table exists with columns: calendar_date, storeNbr, store_notes, mkt_notes, good, top_3, rating")
        raise

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
    calendar_date: str
    storeNbr: str
    store_notes: str
    mkt_notes: str
    good: list[str]
    top_3: list[str]
    rating: str

# --- AI Model Setup ---
# Define the JSON schema for the model's output
response_schema = {
    "type": "OBJECT",
    "properties": {
        "calendar_date": {"type": "STRING"},
        "storeNbr": {"type": "STRING"},
        "store_notes": {"type": "STRING"},
        "mkt_notes": {"type": "STRING"},
        "good": {"type": "ARRAY", "items": {"type": "STRING"}},
        "top_3": {"type": "ARRAY", "items": {"type": "STRING"}},
        "rating": {"type": "STRING"},
    },
    "required": ["calendar_date", "storeNbr", "store_notes", "mkt_notes", "good", "top_3", "rating"]
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

    Extraction Rules:
    - calendar_date: Look for a date in MM/DD/YYYY format (e.g., 11/11/2025). Extract exactly as written.
    - storeNbr: Look for a store number (just digits, e.g., 2617). Return as a string.
    - store_notes: Extract the main body of notes that are TO the store (not the "me:" section).
    - mkt_notes: Look for notes after "me:" label. This is what the store told you. Extract everything after "me:".
    - good: Extract a list of things that were good at the store.
    - top_3: Extract a list of the top 3 things the store needs to fix or do.
    - rating: Look for "Red", "Yellow", or "Green" in the notes. If found, return exactly (Red, Yellow, or Green). If not found, return "Not Rated".
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

        # 1. Create a row to insert with the extracted data:
        # Convert arrays to newline-separated strings for BigQuery
        good_str = "\n".join(parsed_data["good"]) if parsed_data["good"] else ""
        top_3_str = "\n".join(parsed_data["top_3"]) if parsed_data["top_3"] else ""

        row_to_insert = {
            "calendar_date": parsed_data["calendar_date"],
            "storeNbr": parsed_data["storeNbr"],
            "store_notes": parsed_data["store_notes"],
            "mkt_notes": parsed_data["mkt_notes"],
            "good": good_str,
            "top_3": top_3_str,
            "rating": parsed_data["rating"]
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