"""
Summary Tools
Tools for getting overall statistics and summaries.
"""

import json
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection


def get_summary_stats() -> str:
    """
    Get overall summary statistics for all store visits.

    Returns:
        JSON string with total visits, store count, date range,
        and overall rating distribution
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                COUNT(*) as total_visits,
                COUNT(DISTINCT "storeNbr") as unique_stores,
                MIN(calendar_date) as first_visit,
                MAX(calendar_date) as last_visit,
                SUM(CASE WHEN rating = 'Green' THEN 1 ELSE 0 END) as green_count,
                SUM(CASE WHEN rating = 'Yellow' THEN 1 ELSE 0 END) as yellow_count,
                SUM(CASE WHEN rating = 'Red' THEN 1 ELSE 0 END) as red_count
            FROM store_visits
        """)
        stats = cursor.fetchone()

        # Get recent activity (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) as recent_visits
            FROM store_visits
            WHERE calendar_date >= CURRENT_DATE - INTERVAL '30 days'
        """)
        recent = cursor.fetchone()

        cursor.close()

        result = dict(stats) if stats else {}
        result['recent_visits_30d'] = recent['recent_visits'] if recent else 0

        if result.get('first_visit'):
            result['first_visit'] = result['first_visit'].isoformat()
        if result.get('last_visit'):
            result['last_visit'] = result['last_visit'].isoformat()

        return json.dumps(result, default=str)
    finally:
        release_db_connection(conn)
