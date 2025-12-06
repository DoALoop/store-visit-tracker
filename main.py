import os
import json
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from flask import Flask, request, jsonify, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# --- Configuration ---
# Vertex AI configuration
PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "store-visit-tracker")
LOCATION = os.environ.get("GOOGLE_LOCATION", "us-central1")

# PostgreSQL configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "store_visits")
DB_USER = os.environ.get("DB_USER", "store_tracker")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
TABLE_NAME = "store_visits"

# Initialize PostgreSQL connection pool
try:
    db_pool = SimpleConnectionPool(
        1, 20,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print("Successfully connected to PostgreSQL.")
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
    db_pool = None

# Helper functions for database connections
def get_db_connection():
    if db_pool:
        return db_pool.getconn()
    return None

def release_db_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)

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
    if not db_pool:
        return jsonify({"error": "Server is not configured to connect to database."}), 500

    store_number = request.args.get('storeNbr')
    conn = get_db_connection()

    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if store_number:
            # Case 2: Get Prior 3 Visits for a Specific Store
            print(f"Querying for prior 3 visits for store: {store_number}")
            query = """
                SELECT *
                FROM store_visits
                WHERE "storeNbr" = %s
                ORDER BY calendar_date DESC
                LIMIT 3
            """
            cursor.execute(query, (store_number,))
        else:
            # Case 1: Get All Visits
            print("Querying for all recent visits.")
            query = """
                SELECT *
                FROM store_visits
                ORDER BY calendar_date DESC
                LIMIT 100
            """
            cursor.execute(query)

        results = cursor.fetchall()
        cursor.close()

        # Convert date objects to ISO format strings
        for row in results:
            if row.get('calendar_date'):
                row['calendar_date'] = row['calendar_date'].isoformat()

        return jsonify(results)
    except Exception as e:
        print(f"An error occurred during query: {e}")
        return jsonify({"error": "Failed to fetch data from database."}), 500
    finally:
        release_db_connection(conn)

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
You are an AI assistant specializing in digitizing handwritten store visit notes for a District Manager.

Your primary task is to carefully read and transcribe ALL handwritten text from the provided image with high accuracy.

⚠️ CRITICAL - DO NOT HALLUCINATE:
- ONLY extract information that is explicitly written on the paper
- DO NOT invent, assume, or fill in any information that is not clearly visible
- DO NOT make up store numbers, dates, ratings, or notes
- If you cannot read something clearly, use null rather than guessing
- If a section is blank or not present, return null or empty array [] - DO NOT create placeholder content
- When uncertain about a word, either transcribe your best reading of what's actually written OR use null
- DO NOT add context, explanations, or interpretations beyond what is written
- DO NOT standardize or "clean up" the notes - preserve the original wording exactly as written

CRITICAL INSTRUCTIONS FOR HANDWRITING EXTRACTION:
- Read every word carefully, even if handwriting is messy or unclear
- If a word is difficult to read, make your best interpretation based on context AND what's actually written
- Preserve the original meaning and wording as closely as possible
- Pay special attention to numbers, dates, and metrics
- Look for common retail abbreviations (comp, WTD, MTD, etc.)
- Each distinct thought or observation should be treated as a separate note/bullet point
- If something is truly illegible, use null instead of guessing

EXTRACT AND STRUCTURE THE FOLLOWING INFORMATION AS JSON:

1. "storeNbr": The store number (typically 3-4 digits, may be written as "Store #1234" or "#1234" or "1234")
   - ONLY if actually written on the page, otherwise null

2. "calendar_date": Visit date in YYYY-MM-DD format (look for dates written as MM/DD/YY, MM-DD-YYYY, or written out)
   - ONLY if a date is actually present, otherwise null

3. "rating": Overall store rating - must be one of: "Green", "Yellow", or "Red" (may be written as G/Y/R or color-coded)
   - ONLY if explicitly marked/written, otherwise null

4. "store_notes": General observations about store condition. 
   - Extract ALL general comments as separate bullet points
   - Each distinct observation = one bullet point
   - Preserve specific details (names, departments, issues mentioned) EXACTLY as written
   - If no notes present, return empty array []
   - DO NOT create generic or assumed notes

5. "mkt_notes": Market or competitive notes (if present)
   - Look for mentions of competitors, market conditions, external factors
   - Return as separate bullet points
   - If no market notes present, return empty array []

6. "good": What's working well - extract as an array of strings
   - Each positive observation = one array item
   - Look for phrases like "good job", "well done", "excellent", team wins
   - ONLY include items explicitly noted as positive
   - If nothing is marked as "good" or positive, return empty array []

7. "top_3": Top 3 opportunities/focus areas - extract as an array of strings
   - Look for action items, problems to fix, coaching opportunities
   - Should prioritize the most critical issues mentioned
   - ONLY include what's actually written - may be 0, 1, 2, or 3 items
   - DO NOT invent opportunities if fewer than 3 are listed

8. "metrics": An object containing the following numerical metrics (use null if not found):
   {
     "sales_comp_yest": number or percentage (ONLY if written),
     "sales_index_yest": number (ONLY if written),
     "sales_comp_wtd": number or percentage (ONLY if written),
     "sales_index_wtd": number (ONLY if written),
     "sales_comp_mtd": number or percentage (ONLY if written),
     "sales_index_mtd": number (ONLY if written),
     "vizpick": number or percentage (ONLY if written),
     "overstock": number (ONLY if written),
     "picks": number (ONLY if written),
     "vizfashion": number or percentage (ONLY if written),
     "modflex": number or percentage (ONLY if written),
     "tag_errors": number (ONLY if written),
     "mods": number (ONLY if written),
     "pcs": number (ONLY if written),
     "pinpoint": number or percentage (ONLY if written)
   }
   - Each metric should be null if not found on the page
   - DO NOT calculate or derive metrics from other numbers

HANDWRITING INTERPRETATION GUIDANCE:
- Common word confusions: "a" vs "o", "n" vs "u", "r" vs "v"
- Numbers: "1" vs "7", "5" vs "S", "0" vs "O"
- When uncertain, consider the retail context (e.g., if you see "cl__n", it's likely "clean")
- Abbreviations are common: dept (department), mgr (manager), assoc (associate), merch (merchandise)
- When truly illegible: use null rather than making something up

OUTPUT FORMAT:
Return ONLY valid JSON with no markdown formatting, no ```json blocks, no explanations.
If a field cannot be found or determined, use null for objects/numbers or empty array [] for lists.

Example structure:
{
  "storeNbr": "1234",
  "calendar_date": "2024-12-05",
  "rating": "Green",
  "store_notes": [
    "Store looks great, well zoned",
    "Heidi doing excellent job with team",
    "Backroom organized and clean"
  ],
  "mkt_notes": [],
  "good": [
    "Strong customer service",
    "Clean salesfloor",
    "Team morale high"
  ],
  "top_3": [
    "Work on features - need more endcaps filled",
    "Apparel folding needs attention"
  ],
  "metrics": {
    "sales_comp_yest": 5.2,
    "sales_index_yest": 102,
    "sales_comp_wtd": null,
    "sales_index_wtd": null,
    ...
  }
}
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
    if not db_pool:
        return jsonify({"error": "Database not connected"}), 500

    data = request.get_json()

    # Simple validation
    required_fields = ['storeNbr', 'calendar_date', 'rating']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()

        # Prepare data for PostgreSQL
        query = """
            INSERT INTO store_visits
            ("storeNbr", calendar_date, rating, store_notes, mkt_notes, good, top_3)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            str(data.get('storeNbr', '')),
            data.get('calendar_date'),  # YYYY-MM-DD
            data.get('rating'),
            data.get('store_notes', ''),
            data.get('mkt_notes', ''),
            "\n".join(data.get('good', [])) if isinstance(data.get('good'), list) else str(data.get('good', '')),
            "\n".join(data.get('top_3', [])) if isinstance(data.get('top_3'), list) else str(data.get('top_3', ''))
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()

        return jsonify({"message": "Visit saved successfully", "data": data})

    except Exception as e:
        conn.rollback()
        print(f"Error saving to PostgreSQL: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)

@app.route('/api/check-duplicate', methods=['GET'])
def check_duplicate():
    if not db_pool:
        return jsonify({"is_duplicate": False, "existing_records": []})

    store_nbr = request.args.get('storeNbr')
    calendar_date = request.args.get('calendar_date')

    if not store_nbr or not calendar_date:
        return jsonify({"error": "Missing parameters"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"is_duplicate": False, "existing_records": []})

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT *
            FROM store_visits
            WHERE "storeNbr" = %s AND calendar_date = %s
        """

        cursor.execute(query, (store_nbr, calendar_date))
        results = cursor.fetchall()
        cursor.close()

        # Convert date objects to ISO format
        for row in results:
            if row.get('calendar_date'):
                row['calendar_date'] = row['calendar_date'].isoformat()

        return jsonify({
            "is_duplicate": len(results) > 0,
            "existing_records": results
        })
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)

@app.route('/api/summary', methods=['GET'])
def get_summary():
    if not db_pool:
        return jsonify({"error": "Server is not configured to connect to database."}), 500

    print("Querying for store summary.")

    # PostgreSQL version using window functions and json aggregation
    query = """
        SELECT
            "storeNbr",
            json_agg(
                json_build_object(
                    'rating', rating,
                    'calendar_date', calendar_date
                )
                ORDER BY calendar_date DESC
            ) FILTER (WHERE row_num <= 2) as recent_visits
        FROM (
            SELECT
                "storeNbr",
                rating,
                calendar_date,
                ROW_NUMBER() OVER (PARTITION BY "storeNbr" ORDER BY calendar_date DESC) as row_num
            FROM store_visits
        ) ranked
        WHERE row_num <= 2
        GROUP BY "storeNbr"
        ORDER BY "storeNbr"
    """

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()

        # Process results to match expected format
        processed_results = []
        for row in results:
            store_data = {
                "storeNbr": row["storeNbr"],
                "recent_visits": []
            }

            # Parse the JSON aggregated visits
            if row.get("recent_visits"):
                for visit in row["recent_visits"]:
                    store_data["recent_visits"].append({
                        "rating": visit["rating"],
                        "calendar_date": visit["calendar_date"] if isinstance(visit["calendar_date"], str) else visit["calendar_date"].isoformat()
                    })

            processed_results.append(store_data)

        return jsonify(processed_results)
    except Exception as e:
        print(f"An error occurred during query: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
