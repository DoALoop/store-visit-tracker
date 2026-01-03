import os
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
            'id': row['id'],
            'text': row['note_text'],
            'sequence': row['sequence']
        }
        for row in rows
    ]

# Initialize Vertex AI
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Load the model - using Gemini 2.5 Flash
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

    # Construct the prompt - optimized for handwriting recognition based on research
    text_prompt = """
You are the world's greatest transcriber of handwritten notes. You have exceptional skill at reading messy, rushed, or unclear handwriting. You excel at deciphering difficult penmanship by analyzing letter shapes, using context clues, and applying your deep knowledge of retail terminology.

YOUR TASK: Transcribe the handwritten text from this image accurately and extract structured data.

=== HANDWRITING TRANSCRIPTION PROCESS ===

STEP 1: SLOW DOWN AND OBSERVE
Before transcribing, take a moment to observe the overall handwriting style:
- Is it cursive, print, or mixed?
- How does this person form their letters? (Look for patterns)
- What pen was used? (Thick/thin lines affect legibility)
- Are there any consistent quirks in their writing?

STEP 2: CHARACTER-BY-CHARACTER ANALYSIS
For each word you encounter:
1. Look at the OVERALL SHAPE of the word first
2. Count the number of humps, loops, and stems
3. Identify definite letters you're confident about
4. Use those anchor letters to decode the uncertain ones
5. Sound out the word phonetically - does it make sense in context?

STEP 3: CONTEXTUAL INFERENCE
When a word is unclear, use these strategies:
- What word would make grammatical sense here?
- What word fits the retail/store context?
- Look at the first and last letters (usually clearer)
- Consider common phrases: "needs work on", "great job", "follow up", "action item"

=== CRITICAL HANDWRITING PATTERNS ===

COMMON LETTER CONFUSIONS (study these carefully):
- a/o/u - In messy writing, these often look identical. Use context!
- n/m/u/w - Count the humps: n=2, m=3, u=1 with curve, w=2 pointed
- r/v/n - The 'r' often looks like a small 'v'. Look for the shoulder.
- e/c/i - In cursive, 'e' has a loop, 'c' is open, 'i' has a dot nearby
- l/i/t - Height matters: 'l' is tall, 'i' is short with dot, 't' has cross
- h/b/k - Look for the loop direction and stem height
- g/q/y - All have descenders. 'g' loops left, 'q' hooks right, 'y' is open
- f/t - Both have crosses, but 'f' descends below the line
- s/5/S - Context determines: word=s, number=5

NUMBER CONFUSIONS:
- 1/7/l - '7' usually has a horizontal stroke at top
- 0/O/o - In metrics context, assume number. 'O' is larger.
- 5/S - In numbers (metrics), assume 5. In words, assume S.
- 6/b - '6' has closed loop at bottom, 'b' has stem extending up
- 8/B - '8' is rounder, 'B' has flat left side
- 9/g/q - '9' is more angular in numbers
- 2/Z - '2' is rounder, 'Z' has sharp angles
- 4/9 - Look at the closed vs open top

CURSIVE-SPECIFIC:
- Letters often connect and blend together
- The end of one letter becomes the start of the next
- Look for the rhythm and flow of connected letters
- Capital letters are usually disconnected

=== RETAIL VOCABULARY DECODER ===

When decoding words, consider these common retail terms:
- Store areas: salesfloor, backroom, receiving, pharmacy, deli, bakery, produce, meat, dairy, frozen, grocery, GM, HBA, apparel, electronics, sporting goods, automotive, garden, seasonal
- Actions: zone, stock, pick, bin, flex, mod, feature, endcap, sidekick, clip strip
- Metrics: comp, index, vizpick, overstock, picks, modflex, FTPR, presub, pinpoint
- Time periods: WTD, MTD, YTD, yesterday, last week
- People: TL (team lead), SM (store manager), ASM, coach, associate, team
- Status: green, yellow, red, clean, zoned, full, empty, worked

COMMON ABBREVIATIONS:
- dept = department, mgr = manager, assoc = associate
- merch = merchandise, recv = receiving, inv = inventory
- SF = salesfloor, BR = backroom, GM = general merchandise
- HBA = health & beauty aids, OTC = over the counter
- SM = store manager, ASM = assistant manager, TL = team lead
- OT = overtime, PTO = paid time off
- w/ = with, w/o = without, b/c = because
- @ = at, # = number, & = and

=== DATA EXTRACTION SCHEMA ===

Extract and return as JSON:

1. "storeNbr": 4-digit store number (look for "#" or "Store" nearby)
   - Example writings: "#2508", "Store 2508", "2508", "St. 2508"

2. "calendar_date": Visit date in YYYY-MM-DD format
   - Look for: MM/DD/YY, MM/DD, or written dates like "Dec 5" or "12/5"
   - Convert to YYYY-MM-DD format (assume current year if not specified)

3. "rating": "Green", "Yellow", or "Red"
   - May be written as: G/Y/R, circled, highlighted, or spelled out
   - May be a checkmark next to a color name

4. "store_notes": Array of general observations (each note = one array item)
   - Transcribe EXACTLY as written, preserving the original wording
   - Each distinct thought or line = separate array entry
   - Include names, departments, specific issues mentioned

5. "mkt_notes": Array of market/competitor notes
   - Look for: "Market", "Mkt", "Me", "M:", or competitor mentions
   - "Me" often means "Market" in this context

6. "good": Array of positive observations
   - Look for: checkmarks, "+", "good", "great", "excellent", wins

7. "top_3": Array of opportunities/action items (0-3 items)
   - Look for: numbered items, bullets, "focus on", "needs", "opportunity"
   - Only include what's actually written

8. "metrics": Object with numerical values (null if not found):
   {
     "sales_comp_yest": Look for "Comp Y", "Comp Yest", yesterday comparison
     "sales_index_yest": Look for "Index Y", yesterday index
     "sales_comp_wtd": Look for "Comp WTD", "WTD Comp", week-to-date
     "sales_index_wtd": Look for "Index WTD"
     "sales_comp_mtd": Look for "Comp MTD", month-to-date
     "sales_index_mtd": Look for "Index MTD"
     "vizpick": Often on LEFT side, "VizPick", "VP", "Viz Pick"
     "overstock": "OS", "O/S", "Overstock"
     "picks": Number of picks
     "vizfashion": "Fashion", "Viz Fashion", "VF" - often on left side
     "modflex": "Modflex", "MF", "Mod Flex"
     "tag_errors": "Tag Err", "Tags", "TE"
     "mods": Mod count
     "pcs": Piece count, "PCS"
     "pinpoint": "Pinpoint", "PP"
     "ftpr": "FTPR", First Time Pick Rate
     "presub": "Presub", "Pre-Sub"
   }
   NOTE: Metrics are often written on the LEFT MARGIN of the paper!

=== OUTPUT RULES ===

1. Return ONLY valid JSON - no markdown, no explanations, no preamble
2. Do NOT add any words like "Here is the transcription:" - just the JSON
3. Do NOT add section separators like "---"
4. Use null for missing values, [] for empty arrays
5. Preserve original wording - do not "clean up" or standardize the notes
6. If truly illegible after careful analysis, use null rather than guessing wildly
7. For notes that are 70%+ legible, make your best interpretation

=== ANTI-HALLUCINATION RULES ===

- ONLY extract what is ACTUALLY WRITTEN on the paper
- Do NOT invent store numbers, dates, or notes
- Do NOT fill in "expected" content that isn't there
- If a section is blank, return null or []
- When uncertain, transcribe your best reading rather than making something up
    """

    try:
        image_part = Part.from_data(
            data=base64.decodebytes(image_b64.encode('utf-8')),
            mime_type=mime_type
        )
        
        generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.1,  # Very low temperature for maximum transcription accuracy
            "top_p": 0.85,       # Focused sampling for consistent results
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

        # Helper function to clean numeric values (remove % and convert to float)
        def clean_numeric(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                # Remove %, commas, and whitespace
                cleaned = value.replace('%', '').replace(',', '').strip()
                if cleaned == '' or cleaned.lower() == 'null':
                    return None
                try:
                    return float(cleaned)
                except ValueError:
                    return None
            return None

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
            # Metrics - cleaned to remove % signs and convert to numbers
            clean_numeric(metrics.get('sales_comp_yest')),
            clean_numeric(metrics.get('sales_index_yest')),
            clean_numeric(metrics.get('sales_comp_wtd')),
            clean_numeric(metrics.get('sales_index_wtd')),
            clean_numeric(metrics.get('sales_comp_mtd')),
            clean_numeric(metrics.get('sales_index_mtd')),
            clean_numeric(metrics.get('vizpick')),
            clean_numeric(metrics.get('overstock')),
            clean_numeric(metrics.get('picks')),
            clean_numeric(metrics.get('vizfashion')),
            clean_numeric(metrics.get('modflex')),
            clean_numeric(metrics.get('tag_errors')),
            clean_numeric(metrics.get('mods')),
            clean_numeric(metrics.get('pcs')),
            clean_numeric(metrics.get('pinpoint')),
            clean_numeric(metrics.get('ftpr')),
            clean_numeric(metrics.get('presub'))
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


@app.route('/api/visits/<int:visit_id>/notes-received', methods=['POST'])
def toggle_notes_received(visit_id):
    """Toggle the notes_received status for a visit"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        notes_received = data.get('notes_received', False)

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE store_visits
            SET notes_received = %s
            WHERE id = %s
        """, (notes_received, visit_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Visit not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "notes_received": notes_received})

    except Exception as e:
        conn.rollback()
        print(f"Error updating notes_received: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/notes/<note_type>/<int:note_id>', methods=['DELETE'])
def delete_note(note_type, note_id):
    """Delete a specific note by type and ID"""
    # Map note types to table names
    table_map = {
        'store': 'store_visit_notes',
        'market': 'store_market_notes',
        'good': 'store_good_notes',
        'improvement': 'store_improvement_notes'
    }

    if note_type not in table_map:
        return jsonify({"error": f"Invalid note type: {note_type}"}), 400

    table_name = table_map[note_type]

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE id = %s", (note_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Note not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Note deleted"})

    except Exception as e:
        conn.rollback()
        print(f"Error deleting note: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/notes/<note_type>/<int:note_id>', methods=['PUT'])
def edit_note(note_type, note_id):
    """Edit a specific note's text by type and ID"""
    # Map note types to table names
    table_map = {
        'store': 'store_visit_notes',
        'market': 'store_market_notes',
        'good': 'store_good_notes',
        'improvement': 'store_improvement_notes'
    }

    if note_type not in table_map:
        return jsonify({"error": f"Invalid note type: {note_type}"}), 400

    table_name = table_map[note_type]

    data = request.get_json()
    new_text = data.get('text', '').strip()

    if not new_text:
        return jsonify({"error": "Note text cannot be empty"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table_name} SET note_text = %s WHERE id = %s", (new_text, note_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Note not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Note updated", "text": new_text})

    except Exception as e:
        conn.rollback()
        print(f"Error editing note: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/visits/<int:visit_id>', methods=['DELETE'])
def delete_visit(visit_id):
    """Delete an entire visit and all its associated notes"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()

        # Delete all related notes from normalized tables first
        cursor.execute("DELETE FROM store_visit_notes WHERE visit_id = %s", (visit_id,))
        cursor.execute("DELETE FROM store_market_notes WHERE visit_id = %s", (visit_id,))
        cursor.execute("DELETE FROM store_good_notes WHERE visit_id = %s", (visit_id,))
        cursor.execute("DELETE FROM store_improvement_notes WHERE visit_id = %s", (visit_id,))
        cursor.execute("DELETE FROM market_note_completions WHERE visit_id = %s", (visit_id,))

        # Delete the visit itself
        cursor.execute("DELETE FROM store_visits WHERE id = %s", (visit_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Visit not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Visit deleted"})

    except Exception as e:
        conn.rollback()
        print(f"Error deleting visit: {e}")
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
    """Get all market notes from all visits with their completion status, assignment, and updates"""
    if not db_pool:
        return jsonify({"error": "Server is not configured to connect to database."}), 500

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if new columns exist (migration 007)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'market_note_completions' AND column_name = 'status'
        """)
        has_new_columns = cursor.fetchone() is not None

        if has_new_columns:
            # Query with new columns (post-migration)
            query = """
                SELECT
                    sv.id as visit_id,
                    sv."storeNbr" as store_nbr,
                    sv.calendar_date,
                    smn.note_text,
                    COALESCE(mnc.completed, FALSE) as completed,
                    mnc.assigned_to,
                    COALESCE(mnc.status, 'new') as status,
                    mnc.completed_at
                FROM store_market_notes smn
                JOIN store_visits sv ON smn.visit_id = sv.id
                LEFT JOIN market_note_completions mnc
                    ON smn.visit_id = mnc.visit_id AND smn.note_text = mnc.note_text
                ORDER BY
                    CASE COALESCE(mnc.status, 'new')
                        WHEN 'in_progress' THEN 1
                        WHEN 'new' THEN 2
                        WHEN 'on_hold' THEN 3
                        WHEN 'completed' THEN 4
                    END,
                    sv.calendar_date DESC,
                    smn.sequence
            """
        else:
            # Legacy query (pre-migration)
            query = """
                SELECT
                    sv.id as visit_id,
                    sv."storeNbr" as store_nbr,
                    sv.calendar_date,
                    smn.note_text,
                    COALESCE(mnc.completed, FALSE) as completed,
                    NULL as assigned_to,
                    CASE WHEN mnc.completed THEN 'completed' ELSE 'new' END as status,
                    mnc.completed_at
                FROM store_market_notes smn
                JOIN store_visits sv ON smn.visit_id = sv.id
                LEFT JOIN market_note_completions mnc
                    ON smn.visit_id = mnc.visit_id AND smn.note_text = mnc.note_text
                ORDER BY sv.calendar_date DESC, smn.sequence
            """

        cursor.execute(query)
        results = cursor.fetchall()

        # Get updates for each note (only if table exists)
        all_updates = []
        if has_new_columns:
            try:
                updates_query = """
                    SELECT id, visit_id, note_text, update_text, created_by, created_at
                    FROM market_note_updates
                    ORDER BY created_at DESC
                """
                cursor.execute(updates_query)
                all_updates = cursor.fetchall()
            except Exception:
                pass  # Table doesn't exist yet

        # Group updates by visit_id and note_text
        updates_map = {}
        for upd in all_updates:
            key = (upd['visit_id'], upd['note_text'])
            if key not in updates_map:
                updates_map[key] = []
            updates_map[key].append({
                "id": upd['id'],
                "text": upd['update_text'],
                "created_by": upd['created_by'],
                "created_at": upd['created_at'].isoformat() if upd['created_at'] else None
            })

        cursor.close()

        # Build response from normalized data
        market_notes = []
        for row in results:
            key = (row['visit_id'], row['note_text'])
            market_notes.append({
                "visit_id": row['visit_id'],
                "store_nbr": row['store_nbr'],
                "calendar_date": row['calendar_date'].isoformat() if row['calendar_date'] else None,
                "note_text": row['note_text'],
                "completed": row['completed'],
                "assigned_to": row['assigned_to'],
                "status": row['status'],
                "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None,
                "updates": updates_map.get(key, [])
            })

        return jsonify(market_notes)

    except Exception as e:
        print(f"Error fetching market notes: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/market-notes/update', methods=['POST'])
def update_market_note():
    """Update a market note's status, assignment, or completion"""
    if not db_pool:
        return jsonify({"error": "Database not connected"}), 500

    data = request.get_json()

    # Validate required fields
    if not all(key in data for key in ['visit_id', 'note_text']):
        return jsonify({"error": "Missing required fields: visit_id, note_text"}), 400

    visit_id = data['visit_id']
    note_text = data['note_text']
    status = data.get('status')
    assigned_to = data.get('assigned_to')
    completed = data.get('completed')

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        from datetime import datetime

        # Check if new columns exist (migration 007)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'market_note_completions' AND column_name = 'status'
        """)
        has_new_columns = cursor.fetchone() is not None

        # Determine completed_at based on status
        completed_at = None
        if status == 'completed':
            completed = True
            completed_at = datetime.now()
        elif completed:
            completed_at = datetime.now()

        if has_new_columns:
            query = """
                INSERT INTO market_note_completions (visit_id, note_text, completed, completed_at, status, assigned_to)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (visit_id, note_text)
                DO UPDATE SET
                    completed = COALESCE(EXCLUDED.completed, market_note_completions.completed),
                    completed_at = COALESCE(EXCLUDED.completed_at, market_note_completions.completed_at),
                    status = COALESCE(EXCLUDED.status, market_note_completions.status),
                    assigned_to = COALESCE(EXCLUDED.assigned_to, market_note_completions.assigned_to)
            """
            cursor.execute(query, (visit_id, note_text, completed, completed_at, status, assigned_to))
        else:
            # Legacy query without new columns
            query = """
                INSERT INTO market_note_completions (visit_id, note_text, completed, completed_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (visit_id, note_text)
                DO UPDATE SET
                    completed = COALESCE(EXCLUDED.completed, market_note_completions.completed),
                    completed_at = COALESCE(EXCLUDED.completed_at, market_note_completions.completed_at)
            """
            cursor.execute(query, (visit_id, note_text, completed, completed_at))

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Market note updated"})

    except Exception as e:
        conn.rollback()
        print(f"Error updating market note: {e}")
        return jsonify({"error": str(e), "success": False}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/market-notes/add-update', methods=['POST'])
def add_market_note_update():
    """Add an update/comment to a market note"""
    if not db_pool:
        return jsonify({"error": "Database not connected"}), 500

    data = request.get_json()

    # Validate required fields
    if not all(key in data for key in ['visit_id', 'note_text', 'update_text']):
        return jsonify({"error": "Missing required fields: visit_id, note_text, update_text"}), 400

    visit_id = data['visit_id']
    note_text = data['note_text']
    update_text = data['update_text']
    created_by = data.get('created_by', '')

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            INSERT INTO market_note_updates (visit_id, note_text, update_text, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """

        cursor.execute(query, (visit_id, note_text, update_text, created_by))
        result = cursor.fetchone()

        conn.commit()
        cursor.close()

        return jsonify({
            "success": True,
            "update": {
                "id": result['id'],
                "text": update_text,
                "created_by": created_by,
                "created_at": result['created_at'].isoformat() if result['created_at'] else None
            }
        })

    except Exception as e:
        conn.rollback()
        print(f"Error adding market note update: {e}")
        return jsonify({"error": str(e), "success": False}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/market-notes/delete-update/<int:update_id>', methods=['DELETE'])
def delete_market_note_update(update_id):
    """Delete an update/comment from a market note"""
    if not db_pool:
        return jsonify({"error": "Database not connected"}), 500

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM market_note_updates WHERE id = %s", (update_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Update not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Update deleted"})

    except Exception as e:
        conn.rollback()
        print(f"Error deleting market note update: {e}")
        return jsonify({"error": str(e), "success": False}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/market-notes/toggle', methods=['POST'])
def toggle_market_note():
    """Toggle the completion status of a market note (legacy endpoint)"""
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

        # When completing, also update status to 'completed'
        status = 'completed' if completed else 'new'
        completed_at = datetime.now() if completed else None

        query = """
            INSERT INTO market_note_completions (visit_id, note_text, completed, completed_at, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (visit_id, note_text)
            DO UPDATE SET
                completed = EXCLUDED.completed,
                completed_at = EXCLUDED.completed_at,
                status = EXCLUDED.status
        """

        cursor.execute(query, (
            visit_id,
            note_text,
            completed,
            completed_at,
            status
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


# --- Gold Star Notes API ---

def get_current_week_start():
    """Get the Saturday of the current week (weeks start on Saturday)"""
    from datetime import datetime, timedelta
    today = datetime.now().date()
    # Calculate days since Saturday: Sat=0, Sun=1, Mon=2, etc.
    days_since_saturday = (today.weekday() + 2) % 7
    saturday = today - timedelta(days=days_since_saturday)
    return saturday

def get_fiscal_week_number(week_start_date):
    """Calculate fiscal week number (Week 1 starts January 31st)"""
    from datetime import date

    # Determine fiscal year - if before Jan 31, use previous year
    year = week_start_date.year
    fiscal_year_start = date(year, 1, 31)

    if week_start_date < fiscal_year_start:
        # We're in the previous fiscal year
        fiscal_year_start = date(year - 1, 1, 31)

    # Calculate days since fiscal year start
    days_since_start = (week_start_date - fiscal_year_start).days

    # Calculate week number (Week 1 = 0-6 days, Week 2 = 7-13 days, etc.)
    week_number = (days_since_start // 7) + 1

    return week_number

# Market to store mapping
MARKET_STORES = {
    '399': ['1951', '2508', '2617', '2780', '2781', '2861', '2862', '3093', '3739', '5841'],
    '451': ['2002', '2117', '2280', '2458', '4488', '5435', '5751', '5766', '5884']
}

def get_stores_for_market(market):
    """Get list of stores for a given market"""
    if market == 'all' or not market:
        return MARKET_STORES['399'] + MARKET_STORES['451']
    return MARKET_STORES.get(market, [])

@app.route('/api/gold-stars/current', methods=['GET'])
def get_current_gold_stars():
    """Get gold star notes with store completions filtered by market and week offset"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get week offset from query params (-1 = previous week, 0 = current, 1 = next)
        week_offset = int(request.args.get('week_offset', 0))
        current_week_start = get_current_week_start()
        week_start = current_week_start + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)  # Friday

        # Calculate if this is current week (for UI purposes)
        is_current_week = (week_offset == 0)

        # Get market filter from query params
        market = request.args.get('market', 'all')
        market_stores = get_stores_for_market(market)

        # Get current week's gold stars, create if doesn't exist
        cursor.execute("""
            SELECT id, week_start_date, note_1, note_2, note_3, created_at
            FROM gold_star_weeks
            WHERE week_start_date = %s
        """, (week_start,))
        week_data = cursor.fetchone()

        if not week_data:
            # Auto-create the week record with empty notes
            cursor.execute("""
                INSERT INTO gold_star_weeks (week_start_date, note_1, note_2, note_3)
                VALUES (%s, '', '', '')
                RETURNING id, week_start_date, note_1, note_2, note_3, created_at
            """, (week_start,))
            week_data = cursor.fetchone()
            conn.commit()

        # Use market stores list (predefined, not from visits)
        stores = sorted(market_stores)

        # Get completions for this week
        cursor.execute("""
            SELECT store_nbr, note_number, completed
            FROM gold_star_completions
            WHERE week_id = %s
        """, (week_data['id'],))
        completions = cursor.fetchall()

        # Build completion map
        completion_map = {}
        for c in completions:
            key = c['store_nbr']
            if key not in completion_map:
                completion_map[key] = {1: False, 2: False, 3: False}
            completion_map[key][c['note_number']] = c['completed']

        # Build store list with completions
        store_list = []
        for store_nbr in stores:
            store_completions = completion_map.get(store_nbr, {1: False, 2: False, 3: False})
            store_list.append({
                "store_nbr": store_nbr,
                "note_1": store_completions.get(1, False),
                "note_2": store_completions.get(2, False),
                "note_3": store_completions.get(3, False)
            })

        cursor.close()

        return jsonify({
            "week_id": week_data['id'],
            "week_number": get_fiscal_week_number(week_start),
            "week_start_date": str(week_start),
            "week_end_date": str(week_end),
            "week_offset": week_offset,
            "is_current_week": is_current_week,
            "market": market,
            "notes": {
                "note_1": week_data['note_1'],
                "note_2": week_data['note_2'],
                "note_3": week_data['note_3']
            },
            "stores": store_list
        })

    except Exception as e:
        print(f"Error fetching gold stars: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/gold-stars/week', methods=['POST'])
def save_gold_star_week():
    """Create or update the current week's gold star notes"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        note_1 = data.get('note_1', '').strip()
        note_2 = data.get('note_2', '').strip()
        note_3 = data.get('note_3', '').strip()

        if not all([note_1, note_2, note_3]):
            return jsonify({"error": "All three notes are required"}), 400

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        week_start = get_current_week_start()

        # Upsert the week's notes
        cursor.execute("""
            INSERT INTO gold_star_weeks (week_start_date, note_1, note_2, note_3, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (week_start_date)
            DO UPDATE SET note_1 = %s, note_2 = %s, note_3 = %s, updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (week_start, note_1, note_2, note_3, note_1, note_2, note_3))

        week_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()

        return jsonify({"success": True, "week_id": week_id, "message": "Gold star notes saved"})

    except Exception as e:
        conn.rollback()
        print(f"Error saving gold star week: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/gold-stars/toggle', methods=['POST'])
def toggle_gold_star_completion():
    """Toggle a store's completion status for a gold star note"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        store_nbr = data.get('store_nbr')
        note_number = data.get('note_number')
        completed = data.get('completed', False)

        if not store_nbr or not note_number:
            return jsonify({"error": "store_nbr and note_number are required"}), 400

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        week_start = get_current_week_start()

        # Get current week ID
        cursor.execute("""
            SELECT id FROM gold_star_weeks WHERE week_start_date = %s
        """, (week_start,))
        week_row = cursor.fetchone()

        if not week_row:
            return jsonify({"error": "No gold star notes defined for this week"}), 404

        week_id = week_row['id']

        # Upsert completion status
        cursor.execute("""
            INSERT INTO gold_star_completions (week_id, store_nbr, note_number, completed, completed_at)
            VALUES (%s, %s, %s, %s, CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END)
            ON CONFLICT (week_id, store_nbr, note_number)
            DO UPDATE SET completed = %s, completed_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END
        """, (week_id, store_nbr, note_number, completed, completed, completed, completed))

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Completion status updated"})

    except Exception as e:
        conn.rollback()
        print(f"Error toggling gold star completion: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/gold-stars/stores', methods=['GET'])
def get_all_stores():
    """Get list of all unique store numbers from visits"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT DISTINCT "storeNbr" as store_nbr
            FROM store_visits
            WHERE "storeNbr" IS NOT NULL
            ORDER BY "storeNbr"
        """)
        stores = [row['store_nbr'] for row in cursor.fetchall()]
        cursor.close()

        return jsonify(stores)

    except Exception as e:
        print(f"Error fetching stores: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


# --- Champions API ---

@app.route('/api/champions', methods=['GET'])
def get_champions():
    """Get all champions"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, name, responsibility, created_at
            FROM champions
            ORDER BY name, responsibility
        """)
        champions = cursor.fetchall()
        cursor.close()

        # Convert to list of dicts
        result = []
        for c in champions:
            result.append({
                "id": c['id'],
                "name": c['name'],
                "responsibility": c['responsibility'],
                "created_at": str(c['created_at']) if c['created_at'] else None
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error fetching champions: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/champions', methods=['POST'])
def add_champion():
    """Add a new champion"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        responsibility = data.get('responsibility', '').strip()

        if not name or not responsibility:
            return jsonify({"error": "Name and responsibility are required"}), 400

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO champions (name, responsibility)
            VALUES (%s, %s)
            RETURNING id, name, responsibility, created_at
        """, (name, responsibility))

        new_champion = cursor.fetchone()
        conn.commit()
        cursor.close()

        return jsonify({
            "success": True,
            "champion": {
                "id": new_champion['id'],
                "name": new_champion['name'],
                "responsibility": new_champion['responsibility'],
                "created_at": str(new_champion['created_at'])
            }
        })

    except Exception as e:
        conn.rollback()
        print(f"Error adding champion: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/champions/<int:champion_id>', methods=['PUT'])
def update_champion(champion_id):
    """Update a champion"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        responsibility = data.get('responsibility', '').strip()

        if not name or not responsibility:
            return jsonify({"error": "Name and responsibility are required"}), 400

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE champions
            SET name = %s, responsibility = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (name, responsibility, champion_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Champion not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Champion updated"})

    except Exception as e:
        conn.rollback()
        print(f"Error updating champion: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/champions/<int:champion_id>', methods=['DELETE'])
def delete_champion(champion_id):
    """Delete a champion"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM champions WHERE id = %s", (champion_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Champion not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Champion deleted"})

    except Exception as e:
        conn.rollback()
        print(f"Error deleting champion: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


# --- Status Endpoint ---
@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server and connection status for diagnostics"""
    import time
    from datetime import datetime

    status = {
        "server": {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": "development" if app.debug else "production"
        },
        "database": {
            "status": "unknown",
            "host": DB_HOST,
            "port": DB_PORT,
            "name": DB_NAME,
            "latency_ms": None
        },
        "vertex_ai": {
            "status": "unknown",
            "project": PROJECT_ID,
            "location": LOCATION
        },
        "endpoints": []
    }

    # Test database connection
    try:
        start_time = time.time()
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            release_db_connection(conn)
            latency = (time.time() - start_time) * 1000
            status["database"]["status"] = "connected"
            status["database"]["latency_ms"] = round(latency, 2)
        else:
            status["database"]["status"] = "disconnected"
            status["database"]["error"] = "Connection pool not available"
    except Exception as e:
        status["database"]["status"] = "error"
        status["database"]["error"] = str(e)

    # Test Vertex AI status (just check if initialized)
    try:
        if PROJECT_ID and LOCATION:
            status["vertex_ai"]["status"] = "configured"
        else:
            status["vertex_ai"]["status"] = "not configured"
    except Exception as e:
        status["vertex_ai"]["status"] = "error"
        status["vertex_ai"]["error"] = str(e)

    # List available endpoints
    status["endpoints"] = [
        {"path": "/api/visits", "methods": ["GET"]},
        {"path": "/api/save-visit", "methods": ["POST"]},
        {"path": "/api/analyze-visit", "methods": ["POST"]},
        {"path": "/api/market-notes", "methods": ["GET"]},
        {"path": "/api/gold-stars/current", "methods": ["GET"]},
        {"path": "/api/champions", "methods": ["GET", "POST"]},
        {"path": "/api/issues", "methods": ["GET", "POST"]},
        {"path": "/api/status", "methods": ["GET"]}
    ]

    return jsonify(status)


# --- Issues/Feedback Endpoints ---
@app.route('/api/issues', methods=['GET'])
def get_issues():
    """Get all issues/feedback items"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, type, title, description, status, created_at, updated_at, completed_at
            FROM issues
            ORDER BY
                CASE status
                    WHEN 'new' THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'completed' THEN 3
                END,
                created_at DESC
        """)
        issues = cursor.fetchall()
        cursor.close()

        # Convert to serializable format
        result = []
        for issue in issues:
            result.append({
                "id": issue["id"],
                "type": issue["type"],
                "title": issue["title"],
                "description": issue["description"],
                "status": issue["status"],
                "created_at": issue["created_at"].isoformat() if issue["created_at"] else None,
                "updated_at": issue["updated_at"].isoformat() if issue["updated_at"] else None,
                "completed_at": issue["completed_at"].isoformat() if issue["completed_at"] else None
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error fetching issues: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/issues', methods=['POST'])
def add_issue():
    """Add a new issue/feedback item"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        issue_type = data.get('type', '').strip()
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()

        if not issue_type or issue_type not in ['feature', 'bug', 'feedback']:
            return jsonify({"error": "Valid type is required (feature, bug, feedback)"}), 400
        if not title:
            return jsonify({"error": "Title is required"}), 400

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO issues (type, title, description, status)
            VALUES (%s, %s, %s, 'new')
            RETURNING id, type, title, description, status, created_at
        """, (issue_type, title, description))

        new_issue = cursor.fetchone()
        conn.commit()
        cursor.close()

        return jsonify({
            "success": True,
            "issue": {
                "id": new_issue["id"],
                "type": new_issue["type"],
                "title": new_issue["title"],
                "description": new_issue["description"],
                "status": new_issue["status"],
                "created_at": new_issue["created_at"].isoformat() if new_issue["created_at"] else None
            }
        })

    except Exception as e:
        conn.rollback()
        print(f"Error adding issue: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/issues/<int:issue_id>', methods=['PUT'])
def update_issue(issue_id):
    """Update an issue's status or details"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        status = data.get('status')
        title = data.get('title')
        description = data.get('description')
        issue_type = data.get('type')

        cursor = conn.cursor()

        # Build dynamic update query
        updates = []
        params = []

        if status:
            if status not in ['new', 'in_progress', 'completed']:
                return jsonify({"error": "Invalid status"}), 400
            updates.append("status = %s")
            params.append(status)
            if status == 'completed':
                updates.append("completed_at = CURRENT_TIMESTAMP")
            else:
                updates.append("completed_at = NULL")

        if issue_type:
            if issue_type not in ['feature', 'bug', 'feedback']:
                return jsonify({"error": "Invalid type"}), 400
            updates.append("type = %s")
            params.append(issue_type)

        if title is not None:
            updates.append("title = %s")
            params.append(title.strip())

        if description is not None:
            updates.append("description = %s")
            params.append(description.strip())

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(issue_id)

        query = f"UPDATE issues SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)

        if cursor.rowcount == 0:
            return jsonify({"error": "Issue not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Issue updated"})

    except Exception as e:
        conn.rollback()
        print(f"Error updating issue: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@app.route('/api/issues/<int:issue_id>', methods=['DELETE'])
def delete_issue(issue_id):
    """Delete an issue"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM issues WHERE id = %s", (issue_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Issue not found"}), 404

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Issue deleted"})

    except Exception as e:
        conn.rollback()
        print(f"Error deleting issue: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


# --- Chatbot API ---
@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages via ADK agent"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Import chatbot tools
        from chatbot_agent import (
            search_visits, get_visit_details, analyze_trends,
            compare_stores, search_notes, get_summary_stats, get_market_insights,
            get_market_note_status, get_market_note_updates, get_gold_stars,
            get_champions, get_issues
        )

        # ADK agent is optional - use Gemini fallback for now
        # (ADK integration can be added later when API stabilizes)

        # Fallback: Use Gemini directly with tool results
        # Parse the message and call appropriate tool
        message_lower = message.lower()
        import re

        tool_response = None

        # Extract store numbers and rating from message
        numbers = re.findall(r'\b\d{4,5}\b', message)
        rating_filter = None
        if 'green' in message_lower:
            rating_filter = 'Green'
        elif 'yellow' in message_lower:
            rating_filter = 'Yellow'
        elif 'red' in message_lower:
            rating_filter = 'Red'

        # Extract status filter for market notes/issues
        status_filter = None
        if 'in progress' in message_lower or 'in_progress' in message_lower:
            status_filter = 'in_progress'
        elif 'on hold' in message_lower or 'on_hold' in message_lower:
            status_filter = 'on_hold'
        elif 'completed' in message_lower or 'done' in message_lower:
            status_filter = 'completed'
        elif 'new' in message_lower or 'open' in message_lower:
            status_filter = 'new' if 'market' in message_lower else 'open'

        # Route to appropriate tool based on message content
        if 'champion' in message_lower or 'team' in message_lower or 'assigned' in message_lower or 'who is' in message_lower:
            tool_response = get_champions()
        elif 'gold star' in message_lower or 'goldstar' in message_lower:
            tool_response = get_gold_stars()
        elif 'issue' in message_lower or 'feedback' in message_lower or 'bug' in message_lower:
            type_filter = 'feedback' if 'feedback' in message_lower else ('issue' if 'issue' in message_lower or 'bug' in message_lower else None)
            tool_response = get_issues(status_filter=status_filter, type_filter=type_filter)
        elif 'market' in message_lower and ('status' in message_lower or 'progress' in message_lower or 'assigned' in message_lower or 'completion' in message_lower):
            tool_response = get_market_note_status(status_filter=status_filter)
        elif 'market' in message_lower and 'update' in message_lower:
            tool_response = get_market_note_updates()
        elif 'summary' in message_lower or 'stats' in message_lower or 'overview' in message_lower:
            tool_response = get_summary_stats()
        elif 'market' in message_lower and ('insight' in message_lower or 'note' in message_lower):
            tool_response = get_market_insights()
        elif 'compare' in message_lower:
            if numbers:
                tool_response = compare_stores(','.join(numbers))
        elif 'trend' in message_lower or 'analysis' in message_lower:
            if numbers:
                tool_response = analyze_trends(numbers[0])
        elif 'search' in message_lower or 'find' in message_lower:
            # Check if searching for keyword in notes
            match = re.search(r'(?:search|find)\s+(?:for\s+)?(?:stores?\s+with\s+)?["\']?([^"\']+)["\']?', message_lower)
            if match:
                keyword = match.group(1).strip()
                # Don't search for rating words as keywords
                if keyword not in ['green', 'yellow', 'red', 'visits', 'visit', 'store', 'stores']:
                    tool_response = search_notes(keyword)
            # If no keyword match but has store number, search visits
            if not tool_response and numbers:
                tool_response = search_visits(numbers[0], limit=5, rating=rating_filter)
        elif numbers:
            # Has store number - search visits with optional rating filter
            tool_response = search_visits(numbers[0], limit=5, rating=rating_filter)
        else:
            tool_response = get_summary_stats()

        # Use Gemini to generate natural language response
        if tool_response:
            import json
            tool_data = json.loads(tool_response)

            prompt = f"""You are Jax, a helpful assistant for analyzing store visit data. Answer the user's question based on the data provided.

User's question: {message}

Data from database:
{json.dumps(tool_data, indent=2)}

Instructions:
- "Top 3 Notes" or "Top 3" refers to the top_3 field - these are the top improvement opportunities/action items
- store_notes = general store observations
- market_notes = market-level observations
- good_notes = positive observations (what's going well)
- top_3 = Top 3 improvement opportunities (action items)
- Gold Stars = weekly focus areas that stores need to complete
- Champions = team members and their assigned responsibilities
- Issues/Feedback = tracked problems or suggestions with status (open, in_progress, resolved, closed)
- Market note status = tracks if market notes are new, in_progress, on_hold, or completed, and who they're assigned to
- When showing notes or items, list them as a numbered or bulleted list
- Include specific numbers, dates, names, and statuses when relevant
- Be conversational but informative
- If data is missing or doesn't answer the question, say so"""

            try:
                response = model.generate_content(prompt)
                return jsonify({"response": response.text, "source": "gemini_fallback"})
            except Exception as e:
                print(f"Gemini error: {e}")
                return jsonify({
                    "response": f"Here's what I found:\n\n{json.dumps(tool_data, indent=2)}",
                    "source": "raw_data"
                })

        return jsonify({"error": "Could not process your question"}), 400

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
