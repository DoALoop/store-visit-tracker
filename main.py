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

# Helper functions for normalized note handling
def save_notes_to_db(cursor, visit_id, note_type, notes_list):
    """
    Save notes to the appropriate normalized table.
    
    Args:
        cursor: Database cursor
        visit_id: The visit ID to associate notes with
        note_type: One of 'store', 'market', 'good', 'improvement'
        notes_list: List of note strings
    """
    if not notes_list:
        return
    
    # Map note types to table names
    table_map = {
        'store': 'store_visit_notes',
        'market': 'store_market_notes',
        'good': 'store_good_notes',
        'improvement': 'store_improvement_notes'
    }
    
    table_name = table_map.get(note_type)
    if not table_name:
        raise ValueError(f"Invalid note type: {note_type}")
    
    # Convert to list if needed
    if isinstance(notes_list, str):
        # Handle old format (newline-separated string)
        notes_list = [n.strip() for n in notes_list.split('\n') if n.strip()]
    elif not isinstance(notes_list, list):
        notes_list = []
    
    # Insert each note with sequence number
    for sequence, note_text in enumerate(notes_list, 1):
        if note_text and note_text.strip():  # Only insert non-empty notes
            query = f"""
                INSERT INTO {table_name} (visit_id, note_text, sequence)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (visit_id, note_text.strip(), sequence))

def get_notes_from_db(cursor, visit_id, note_type):
    """
    Retrieve notes from the appropriate normalized table.
    
    Args:
        cursor: Database cursor
        visit_id: The visit ID to retrieve notes for
        note_type: One of 'store', 'market', 'good', 'improvement'
    
    Returns:
        List of note dictionaries with id, text, and sequence
    """
    # Map note types to table names
    table_map = {
        'store': 'store_visit_notes',
        'market': 'store_market_notes',
        'good': 'store_good_notes',
        'improvement': 'store_improvement_notes'
    }
    
    table_name = table_map.get(note_type)
    if not table_name:
        raise ValueError(f"Invalid note type: {note_type}")
    
    query = f"""
        SELECT id, note_text, sequence
        FROM {table_name}
        WHERE visit_id = %s
        ORDER BY sequence ASC
    """
    cursor.execute(query, (visit_id,))
    rows = cursor.fetchall()
    
    return [
        {
            'id': row[0],
            'text': row[1],
            'sequence': row[2]
        }
        for row in rows
    ]

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

        # Add notes from normalized tables to each visit
        for row in results:
            visit_id = row.get('id')
            if visit_id:
                # Query notes from each normalized table
                row['store_notes'] = get_notes_from_db(cursor, visit_id, 'store')
                row['mkt_notes'] = get_notes_from_db(cursor, visit_id, 'market')
                row['good'] = get_notes_from_db(cursor, visit_id, 'good')
                row['top_3'] = get_notes_from_db(cursor, visit_id, 'improvement')
            
            # Convert date objects to ISO format strings
            if row.get('calendar_date'):
                row['calendar_date'] = row['calendar_date'].isoformat()

        cursor.close()
        return jsonify(results)
    except Exception as e:
        print(f"An error occurred during query: {e}")
        return jsonify({"error": "Failed to fetch data from database."}), 500
    finally:
        release_db_connection(conn)

@app.route('/api/visit/<int:visit_id>', methods=['GET'])
def get_visit_detail(visit_id):
    """Get full details of a single visit by ID"""
    if not db_pool:
        return jsonify({"error": "Server is not configured to connect to database."}), 500

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT *
            FROM store_visits
            WHERE id = %s
        """
        cursor.execute(query, (visit_id,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({"error": "Visit not found"}), 404

        # Add notes from normalized tables
        result['store_notes'] = get_notes_from_db(cursor, visit_id, 'store')
        result['mkt_notes'] = get_notes_from_db(cursor, visit_id, 'market')
        result['good'] = get_notes_from_db(cursor, visit_id, 'good')
        result['top_3'] = get_notes_from_db(cursor, visit_id, 'improvement')

        # Convert date object to ISO format string
        if result.get('calendar_date'):
            result['calendar_date'] = result['calendar_date'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()

        cursor.close()
        return jsonify(result)
    except Exception as e:
        print(f"An error occurred while fetching visit detail: {e}")
        return jsonify({"error": "Failed to fetch visit details"}), 500
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
   - Look for sections labeled as: "Market", "Mkt", "Me", "me", "M:", "Market Notes", or similar variations
   - Also look for mentions of competitors, market conditions, external factors even if not explicitly labeled
   - Return as separate bullet points
   - If no market notes present, return empty array []
   - Common abbreviations: "Me" often means "Market", case-insensitive

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
     "sales_comp_yest": number or percentage - Look for: "Comp Yest", "Comp Y", "Yesterday Comp", "Yest Comp"
     "sales_index_yest": number - Look for: "Index Yest", "Index Y", "Yesterday Index", "Yest Index"
     "sales_comp_wtd": number or percentage - Look for: "Comp WTD", "WTD Comp", "Week Comp"
     "sales_index_wtd": number - Look for: "Index WTD", "WTD Index", "Week Index"
     "sales_comp_mtd": number or percentage - Look for: "Comp MTD", "MTD Comp", "Month Comp"
     "sales_index_mtd": number - Look for: "Index MTD", "MTD Index", "Month Index"
     "vizpick": number or percentage - Look for: "Vizpick", "Viz Pick", "VizP", "VP" (often on left side)
     "overstock": number - Look for: "Overstock", "OS", "O/S", "Over Stock"
     "picks": number - Look for: "Picks", "Pick", "P" (context-dependent)
     "vizfashion": number or percentage - Look for: "Viz Fashion", "VizFashion", "Fashion", "Viz F", "VF" (often on left side, may just say "Fashion")
     "modflex": number or percentage - Look for: "Modflex", "Mod Flex", "MF", "Flex"
     "tag_errors": number - Look for: "Tag Errors", "Tags", "Tag Err", "TE"
     "mods": number - Look for: "Mods", "Mod", "M" (context-dependent)
     "pcs": number - Look for: "PCS", "Pcs", "Pieces", "PC"
     "pinpoint": number or percentage - Look for: "Pinpoint", "Pin Point", "PP"
     "ftpr": number or percentage - Look for: "FTPR", "FTPr", "FT PR", "First Time Pass Rate"
     "presub": number or percentage - Look for: "Presub", "Pre-Sub", "Pre Sub", "PS"
   }
   - CRITICAL: Pay special attention to the LEFT SIDE of the paper where metrics like Vizpick, Overstock, Picks, and Viz Fashion are often written
   - Each metric should be null if not found on the page
   - DO NOT calculate or derive metrics from other numbers
   - Extract the number exactly as written (include decimals, percentages)
   - If you see just "Fashion" on the left side, it likely refers to "vizfashion"

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
        error_message = str(e)
        print(f"Error analyzing image: {error_message}")

        # Check for quota-specific errors
        if "quota" in error_message.lower() or "429" in error_message or "resourceExhausted" in error_message:
            return jsonify({
                "error": "AI quota limit reached. Please try again later.",
                "error_type": "quota_exceeded",
                "details": error_message
            }), 429
        elif "503" in error_message or "unavailable" in error_message.lower():
            return jsonify({
                "error": "AI service temporarily unavailable. Please try again.",
                "error_type": "service_unavailable",
                "details": error_message
            }), 503
        else:
            return jsonify({
                "error": error_message,
                "error_type": "analysis_error"
            }), 500

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

        # Extract metrics from nested object
        metrics = data.get('metrics', {})

        # Step 1: Insert visit without notes (normalized structure)
        visit_query = """
            INSERT INTO store_visits
            ("storeNbr", calendar_date, rating,
             sales_comp_yest, sales_index_yest, sales_comp_wtd, sales_index_wtd,
             sales_comp_mtd, sales_index_mtd, vizpick, overstock, picks, vizfashion,
             modflex, tag_errors, mods, pcs, pinpoint, ftpr, presub)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        visit_values = (
            str(data.get('storeNbr', '')),
            data.get('calendar_date'),  # YYYY-MM-DD
            data.get('rating'),
            # Metrics
            metrics.get('sales_comp_yest'),
            metrics.get('sales_index_yest'),
            metrics.get('sales_comp_wtd'),
            metrics.get('sales_index_wtd'),
            metrics.get('sales_comp_mtd'),
            metrics.get('sales_index_mtd'),
            metrics.get('vizpick'),
            metrics.get('overstock'),
            metrics.get('picks'),
            metrics.get('vizfashion'),
            metrics.get('modflex'),
            metrics.get('tag_errors'),
            metrics.get('mods'),
            metrics.get('pcs'),
            metrics.get('pinpoint'),
            metrics.get('ftpr'),
            metrics.get('presub')
        )

        cursor.execute(visit_query, visit_values)
        visit_id = cursor.fetchone()[0]

        # Step 2: Insert notes into normalized tables
        save_notes_to_db(cursor, visit_id, 'store', data.get('store_notes', []))
        save_notes_to_db(cursor, visit_id, 'market', data.get('mkt_notes', []))
        save_notes_to_db(cursor, visit_id, 'good', data.get('good', []))
        save_notes_to_db(cursor, visit_id, 'improvement', data.get('top_3', []))

        # Commit all changes at once (transaction)
        conn.commit()
        cursor.close()

        return jsonify({"message": "Visit saved successfully", "visit_id": visit_id, "data": data})

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

        # Add notes from normalized tables to each visit
        for row in results:
            visit_id = row.get('id')
            if visit_id:
                row['store_notes'] = get_notes_from_db(cursor, visit_id, 'store')
                row['mkt_notes'] = get_notes_from_db(cursor, visit_id, 'market')
                row['good'] = get_notes_from_db(cursor, visit_id, 'good')
                row['top_3'] = get_notes_from_db(cursor, visit_id, 'improvement')
            
            # Convert date objects to ISO format
            if row.get('calendar_date'):
                row['calendar_date'] = row['calendar_date'].isoformat()
        
        cursor.close()

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
@app.route('/api/market-notes', methods=['GET'])
def get_market_notes():
    """Get all market notes from all visits with their completion status"""
    if not db_pool:
        return jsonify({"error": "Server is not configured to connect to database."}), 500

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query to get all visits with market notes and their completion status
        query = """
            SELECT
                sv.id as visit_id,
                sv."storeNbr" as store_nbr,
                sv.calendar_date,
                sv.mkt_notes,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'note_text', mnc.note_text,
                            'completed', mnc.completed,
                            'completed_at', mnc.completed_at
                        )
                    ) FILTER (WHERE mnc.note_text IS NOT NULL),
                    '[]'::json
                ) as completions
            FROM store_visits sv
            LEFT JOIN market_note_completions mnc ON sv.id = mnc.visit_id
            WHERE sv.mkt_notes IS NOT NULL AND sv.mkt_notes != ''
            GROUP BY sv.id, sv."storeNbr", sv.calendar_date, sv.mkt_notes
            ORDER BY sv.calendar_date DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()

        # Process results to expand market notes into individual items
        market_notes = []
        for row in results:
            mkt_notes_text = row['mkt_notes']
            if not mkt_notes_text:
                continue

            # Split market notes by newline to get individual notes
            notes_list = [note.strip() for note in mkt_notes_text.split('\n') if note.strip()]

            # Create completion lookup
            completions_dict = {}
            for comp in row['completions']:
                if comp and 'note_text' in comp:
                    completions_dict[comp['note_text']] = comp['completed']

            # Create an item for each note
            for note_text in notes_list:
                market_notes.append({
                    "visit_id": row['visit_id'],
                    "store_nbr": row['store_nbr'],
                    "calendar_date": row['calendar_date'].isoformat() if row['calendar_date'] else None,
                    "note_text": note_text,
                    "completed": completions_dict.get(note_text, False)
                })

        return jsonify(market_notes)

    except Exception as e:
        print(f"Error fetching market notes: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/market-notes/toggle', methods=['POST'])
def toggle_market_note():
    """Toggle the completion status of a market note"""
    if not db_pool:
        return jsonify({"error": "Database not connected"}), 500

    data = request.get_json()

    # Validate required fields
    if not all(key in data for key in ['visit_id', 'note_text', 'completed']):
        return jsonify({"error": "Missing required fields: visit_id, note_text, completed"}), 400

    visit_id = data['visit_id']
    note_text = data['note_text']
    completed = data['completed']

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()

        # Insert or update the completion status
        from datetime import datetime

        query = """
            INSERT INTO market_note_completions (visit_id, note_text, completed, completed_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (visit_id, note_text)
            DO UPDATE SET
                completed = EXCLUDED.completed,
                completed_at = EXCLUDED.completed_at
        """

        completed_at = datetime.now() if completed else None

        cursor.execute(query, (
            visit_id,
            note_text,
            completed,
            completed_at
        ))

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Market note status updated"})

    except Exception as e:
        conn.rollback()
        print(f"Error toggling market note: {e}")
        return jsonify({"error": str(e), "success": False}), 500
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
