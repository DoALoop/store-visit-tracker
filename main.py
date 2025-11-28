import os
import json
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from flask import Flask, request, jsonify, send_from_directory
from google.cloud import bigquery
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# --- Configuration ---
# Use environment variables provided by Cloud Run, with fallbacks
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "store-visit-tracker")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
DATASET_ID = "store_visits"
TABLE_ID = "store_visits"

# Initialize BigQuery
try:
    bq_client = bigquery.Client(project=PROJECT_ID)
    print("Successfully connected to BigQuery.")
except Exception as e:
    print(f"Error connecting to BigQuery: {e}")
    bq_client = None

# Initialize Vertex AI
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Load the model - using 2.5 Flash (stable alias)
    model = GenerativeModel("gemini-2.5-flash")
    print("Successfully connected to Vertex AI.")
except Exception as e:
    print(f"Error connecting to Vertex AI: {e}")
    model = None

# --- Static File Route ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# --- API Routes ---

@app.route('/api/visits', methods=['GET'])
def get_visits():
    if not bq_client:
        return jsonify({"error": "Server is not configured to connect to BigQuery."}), 500

    store_number = request.args.get('storeNbr')

    if store_number:
        # Case 2: Get Prior 3 Visits for a Specific Store
        print(f"Querying for prior 3 visits for store: {store_number}")
        query = f"""
            SELECT * 
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
            WHERE storeNbr = @store_number 
            ORDER BY calendar_date DESC 
            LIMIT 3
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("store_number", "STRING", store_number),
            ]
        )
    else:
        # Case 1: Get All Visits
        print("Querying for all recent visits.")
        query = f"""
            SELECT * 
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
            ORDER BY calendar_date DESC 
            LIMIT 100
        """
        job_config = bigquery.QueryJobConfig()

    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = [dict(row) for row in query_job]
        return jsonify(results)
    except Exception as e:
        print(f"An error occurred during BigQuery query: {e}")
        return jsonify({"error": "Failed to fetch data from database."}), 500

@app.route('/api/analyze-visit', methods=['POST'])
def analyze_visit():
    if not model:
        return jsonify({"error": "AI Model not initialized."}), 500

    data = request.get_json()
    if not data or 'image_data' not in data:
        return jsonify({"error": "No image data provided"}), 400

    image_b64 = data['image_data']
    mime_type = data.get('mime_type', 'image/jpeg')

    print("Received image for analysis...")

    # Construct the prompt
    text_prompt = """
    You are an AI assistant helping a District Manager digitize their handwritten store visit notes.
    Analyze the provided image of a handwritten note.
    
    Extract the following information and return it as a JSON object:
    1. "storeNbr": The store number (usually a 4-digit number like 1234).
    2. "calendar_date": The date of the visit in YYYY-MM-DD format.
    3. "rating": The store rating. It will be one of: "Green", "Yellow", or "Red".
    4. "store_notes": The general notes/comments about the store condition.
    5. "mkt_notes": Any notes specific to the market or competition (if any).
    6. "good": A list of strings listing what was good.
    7. "top_3": A list of strings listing the top 3 opportunities/things needed.

    If a field is not found, use null or an empty string. 
    Ensure the output is valid JSON. Do not include Markdown formatting (```json).
    """

    try:
        image_part = Part.from_data(
            data=base64.decodebytes(image_b64.encode('utf-8')),
            mime_type=mime_type
        )
        
        generation_config = {
            "max_output_tokens": 8192,
            "temperature": 1,
            "top_p": 0.95,
            "response_mime_type": "application/json",
        }

        responses = model.generate_content(
            [image_part, text_prompt],
            generation_config=generation_config,
            stream=False,
        )
        
        # Parse the response
        response_text = responses.text
        # Clean up any potential markdown formatting just in case
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        parsed_result = json.loads(response_text)
        print("Analysis complete:", parsed_result)
        return jsonify(parsed_result)

    except Exception as e:
        print(f"Error analyzing image: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-visit', methods=['POST'])
def save_visit():
    if not bq_client:
        return jsonify({"error": "Database not connected"}), 500

    data = request.get_json()
    
    # Simple validation
    required_fields = ['storeNbr', 'calendar_date', 'rating']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        # Prepare data for BigQuery
        # Convert lists to strings if necessary, or store as REPEATED fields if your schema supports it.
        # Assuming schema is simple strings for now based on previous interactions.
        
        row_to_insert = {
            "storeNbr": str(data.get('storeNbr', '')),
            "calendar_date": data.get('calendar_date'), # YYYY-MM-DD
            "rating": data.get('rating'),
            "store_notes": data.get('store_notes', ''),
            "mkt_notes": data.get('mkt_notes', ''),
            # Join lists into a single string for storage if table isn't set up for arrays
            # Or assume the table can handle string arrays. 
            # Let's stringify them for safety unless we know the schema matches.
            # Actually, let's try to pass them as provided, if BQ fails we'll know.
            # But to be safe with standard tables:
            "good": "\n".join(data.get('good', [])) if isinstance(data.get('good'), list) else str(data.get('good', '')),
            "top_3": "\n".join(data.get('top_3', [])) if isinstance(data.get('top_3'), list) else str(data.get('top_3', '')),
        }

        errors = bq_client.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}", [row_to_insert])
        
        if errors:
            print(f"BigQuery Insert Errors: {errors}")
            return jsonify({"error": f"Failed to insert rows: {errors}"}), 500
            
        return jsonify({"message": "Visit saved successfully", "data": row_to_insert})

    except Exception as e:
        print(f"Error saving to BigQuery: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-duplicate', methods=['GET'])
def check_duplicate():
    if not bq_client:
        return jsonify({"is_duplicate": False, "existing_records": []})

    store_nbr = request.args.get('storeNbr')
    calendar_date = request.args.get('calendar_date')

    if not store_nbr or not calendar_date:
        return jsonify({"error": "Missing parameters"}), 400

    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE storeNbr = @store_nbr AND calendar_date = @calendar_date
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("store_nbr", "STRING", store_nbr),
            bigquery.ScalarQueryParameter("calendar_date", "DATE", calendar_date),
        ]
    )

    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = [dict(row) for row in query_job]
        
        return jsonify({
            "is_duplicate": len(results) > 0,
            "existing_records": results
        })
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
