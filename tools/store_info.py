"""
Store Information Tool for Jax AI.
"""

import json
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection

def get_store_information(store_number: Optional[str] = None) -> str:
    """
    Get information about specific stores. Includes location, performance tiers, size, manager demographics, etc.
    
    Args:
        store_number: Optional store number (e.g., '1461'). If omitted, returns available context on major store details.
        
    Returns:
        JSON string with the matched store details or a small list of highlighted operations data.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if store_number:
            cursor.execute("""
                SELECT *
                FROM store_info 
                WHERE CAST(store_number AS VARCHAR) = %s
            """, (store_number,))
            result = cursor.fetchall()
        else:
            # When looking for broad store information without a specific store,
            # pull a generalized sample or top-tier lists
            cursor.execute("""
                SELECT store_number, store_format, city, state, volume_tier, 
                       complex_tier, store_manager, last_visit_date 
                FROM store_info 
                ORDER BY CAST(store_number AS INTEGER) ASC
                LIMIT 50
            """)
            result = cursor.fetchall()
            
        # Format dates to avoid JSON serialization errors
        for record in result:
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            if record.get('updated_at'):
                record['updated_at'] = record['updated_at'].isoformat()
            if record.get('last_visit_date'):
                record['last_visit_date'] = record['last_visit_date'].isoformat()

        cursor.close()
        
        if not result:
            return json.dumps({"message": f"No store information found for store {store_number}." if store_number else "No store info directory found."})
            
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": f"Database error fetching store info: {str(e)}"})
    finally:
        release_db_connection(conn)
