"""
Store Visit Tools
Tools for searching, viewing, analyzing, and comparing store visits.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection


def search_visits(store_nbr: str, limit: int = 10, rating: Optional[str] = None) -> str:
    """
    Search for recent visits to a specific store with full details including notes.

    Args:
        store_nbr: The store number to search for
        limit: Maximum number of visits to return (default 10)
        rating: Optional filter by rating (Green, Yellow, Red)

    Returns:
        JSON string with visit details including all metrics and notes
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, "storeNbr", calendar_date, rating,
                   sales_comp_yest, sales_comp_wtd, sales_comp_mtd,
                   sales_index_yest, sales_index_wtd, sales_index_mtd,
                   vizpick, overstock, picks, vizfashion, modflex,
                   tag_errors, mods, pcs, pinpoint, ftpr, presub
            FROM store_visits
            WHERE "storeNbr" = %s
        """
        params = [store_nbr]

        if rating:
            query += " AND LOWER(rating) = LOWER(%s)"
            params.append(rating)

        query += " ORDER BY calendar_date DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        visits = cursor.fetchall()

        # Get notes for each visit
        for visit in visits:
            visit_id = visit['id']

            note_tables = [
                ('store_notes', 'store_visit_notes'),
                ('market_notes', 'store_market_notes'),
                ('good_notes', 'store_good_notes'),
                ('top_3', 'store_improvement_notes')
            ]

            for key, table in note_tables:
                cursor.execute(f"""
                    SELECT note_text FROM {table}
                    WHERE visit_id = %s ORDER BY sequence
                """, (visit_id,))
                visit[key] = [row['note_text'] for row in cursor.fetchall()]

            if visit['calendar_date']:
                visit['calendar_date'] = visit['calendar_date'].isoformat()

        cursor.close()
        return json.dumps(visits, default=str)
    finally:
        release_db_connection(conn)


def get_visit_details(visit_id: int) -> str:
    """
    Get full details for a specific visit including all notes and metrics.

    Args:
        visit_id: The ID of the visit to retrieve

    Returns:
        JSON string with complete visit data including all metrics and notes
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM store_visits WHERE id = %s", (visit_id,))
        visit = cursor.fetchone()

        if not visit:
            return json.dumps({"error": "Visit not found"})

        note_tables = [
            ('store_notes', 'store_visit_notes'),
            ('market_notes', 'store_market_notes'),
            ('good_notes', 'store_good_notes'),
            ('top_3', 'store_improvement_notes')
        ]

        for key, table in note_tables:
            cursor.execute(f"""
                SELECT note_text FROM {table}
                WHERE visit_id = %s ORDER BY sequence
            """, (visit_id,))
            visit[key] = [row['note_text'] for row in cursor.fetchall()]

        cursor.close()

        if visit.get('calendar_date'):
            visit['calendar_date'] = visit['calendar_date'].isoformat()
        if visit.get('created_at'):
            visit['created_at'] = visit['created_at'].isoformat()

        return json.dumps(visit, default=str)
    finally:
        release_db_connection(conn)


def analyze_trends(store_nbr: str, days: int = 90) -> str:
    """
    Analyze trends for a store over a period of time.

    Args:
        store_nbr: The store number to analyze
        days: Number of days to look back (default 90)

    Returns:
        JSON string with trend analysis including rating distribution,
        average metrics, and changes over time
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        start_date = datetime.now() - timedelta(days=days)

        # Get rating distribution
        cursor.execute("""
            SELECT rating, COUNT(*) as count
            FROM store_visits
            WHERE "storeNbr" = %s AND calendar_date >= %s
            GROUP BY rating
        """, (store_nbr, start_date))
        ratings = {row['rating']: row['count'] for row in cursor.fetchall()}

        # Get average metrics
        cursor.execute("""
            SELECT
                COUNT(*) as visit_count,
                AVG(sales_comp_yest) as avg_sales_comp_yest,
                AVG(sales_comp_wtd) as avg_sales_comp_wtd,
                AVG(sales_comp_mtd) as avg_sales_comp_mtd,
                AVG(vizpick) as avg_vizpick,
                AVG(ftpr) as avg_ftpr,
                AVG(overstock) as avg_overstock
            FROM store_visits
            WHERE "storeNbr" = %s AND calendar_date >= %s
        """, (store_nbr, start_date))
        averages = cursor.fetchone()

        # Get recent trend (compare first half vs second half of period)
        mid_date = datetime.now() - timedelta(days=days//2)
        cursor.execute("""
            SELECT
                CASE WHEN calendar_date >= %s THEN 'recent' ELSE 'earlier' END as period,
                AVG(sales_comp_wtd) as avg_sales_comp
            FROM store_visits
            WHERE "storeNbr" = %s AND calendar_date >= %s
            GROUP BY CASE WHEN calendar_date >= %s THEN 'recent' ELSE 'earlier' END
        """, (mid_date, store_nbr, start_date, mid_date))
        trend_data = {row['period']: row['avg_sales_comp'] for row in cursor.fetchall()}

        cursor.close()

        result = {
            "store_nbr": store_nbr,
            "period_days": days,
            "rating_distribution": ratings,
            "averages": dict(averages) if averages else {},
            "trend": trend_data
        }

        return json.dumps(result, default=str)
    finally:
        release_db_connection(conn)


def compare_stores(store_list: str) -> str:
    """
    Compare metrics across multiple stores.

    Args:
        store_list: Comma-separated list of store numbers (e.g., "1234,5678,9012")

    Returns:
        JSON string with side-by-side comparison of key metrics for each store
    """
    stores = [s.strip() for s in store_list.split(',')]
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        results = []
        for store_nbr in stores:
            cursor.execute("""
                SELECT
                    "storeNbr",
                    COUNT(*) as total_visits,
                    SUM(CASE WHEN rating = 'Green' THEN 1 ELSE 0 END) as green_count,
                    SUM(CASE WHEN rating = 'Yellow' THEN 1 ELSE 0 END) as yellow_count,
                    SUM(CASE WHEN rating = 'Red' THEN 1 ELSE 0 END) as red_count,
                    AVG(sales_comp_wtd) as avg_sales_comp,
                    AVG(vizpick) as avg_vizpick,
                    AVG(ftpr) as avg_ftpr,
                    MAX(calendar_date) as last_visit
                FROM store_visits
                WHERE "storeNbr" = %s
                GROUP BY "storeNbr"
            """, (store_nbr,))
            row = cursor.fetchone()
            if row:
                if row.get('last_visit'):
                    row['last_visit'] = row['last_visit'].isoformat()
                results.append(dict(row))

        cursor.close()
        return json.dumps(results, default=str)
    finally:
        release_db_connection(conn)
