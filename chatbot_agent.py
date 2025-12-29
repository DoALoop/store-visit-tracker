"""
Store Visit Analytics Chatbot Agent
Uses Google ADK with Gemini to answer questions about store visits.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import json

# Database tools - these will be called by the ADK agent
# They use the db_pool from main.py when integrated

def get_db_connection():
    """Get database connection from the pool"""
    # This will be replaced with actual pool when integrated into main.py
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "store_visits"),
        user=os.environ.get("DB_USER", "store_tracker"),
        password=os.environ.get("DB_PASSWORD")
    )
    return conn


def search_visits(store_nbr: str, limit: int = 10, rating: str = None) -> str:
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
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        # Build query with optional rating filter
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

            # Get all note types (top_3 = improvement opportunities)
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

            # Convert date
            if visit['calendar_date']:
                visit['calendar_date'] = visit['calendar_date'].isoformat()

        cursor.close()
        return json.dumps(visits, default=str)
    finally:
        conn.close()


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
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        # Get visit record
        cursor.execute("""
            SELECT * FROM store_visits WHERE id = %s
        """, (visit_id,))
        visit = cursor.fetchone()

        if not visit:
            return json.dumps({"error": "Visit not found"})

        # Get notes from normalized tables (top_3 = improvement opportunities)
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

        # Convert dates
        if visit.get('calendar_date'):
            visit['calendar_date'] = visit['calendar_date'].isoformat()
        if visit.get('created_at'):
            visit['created_at'] = visit['created_at'].isoformat()

        return json.dumps(visit, default=str)
    finally:
        conn.close()


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
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

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
        conn.close()


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
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

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
        conn.close()


def search_notes(keyword: str, limit: int = 20) -> str:
    """
    Search for a keyword across all note types.

    Args:
        keyword: The keyword or phrase to search for
        limit: Maximum number of results to return (default 20)

    Returns:
        JSON string with matching notes and their associated visit info
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        # Search across all note tables
        note_tables = [
            ('store', 'store_visit_notes'),
            ('market', 'store_market_notes'),
            ('good', 'store_good_notes'),
            ('improvement', 'store_improvement_notes')
        ]

        results = []
        search_pattern = f'%{keyword}%'

        for note_type, table in note_tables:
            cursor.execute(f"""
                SELECT n.note_text, n.visit_id, v."storeNbr", v.calendar_date, v.rating,
                       %s as note_type
                FROM {table} n
                JOIN store_visits v ON n.visit_id = v.id
                WHERE LOWER(n.note_text) LIKE LOWER(%s)
                ORDER BY v.calendar_date DESC
                LIMIT %s
            """, (note_type, search_pattern, limit))

            for row in cursor.fetchall():
                if row['calendar_date']:
                    row['calendar_date'] = row['calendar_date'].isoformat()
                results.append(dict(row))

        cursor.close()

        # Sort by date and limit total results
        results.sort(key=lambda x: x.get('calendar_date', ''), reverse=True)
        return json.dumps(results[:limit], default=str)
    finally:
        conn.close()


def get_summary_stats() -> str:
    """
    Get overall summary statistics for all store visits.

    Returns:
        JSON string with total visits, store count, date range,
        and overall rating distribution
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

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
        conn.close()


def get_market_insights(days: int = 30) -> str:
    """
    Get aggregated market insights from all stores.

    Args:
        days: Number of days to look back (default 30)

    Returns:
        JSON string with common market observations and themes
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        start_date = datetime.now() - timedelta(days=days)

        cursor.execute("""
            SELECT n.note_text, v."storeNbr", v.calendar_date
            FROM store_market_notes n
            JOIN store_visits v ON n.visit_id = v.id
            WHERE v.calendar_date >= %s
            ORDER BY v.calendar_date DESC
        """, (start_date,))

        notes = []
        for row in cursor.fetchall():
            if row['calendar_date']:
                row['calendar_date'] = row['calendar_date'].isoformat()
            notes.append(dict(row))

        cursor.close()

        return json.dumps({
            "period_days": days,
            "total_market_notes": len(notes),
            "notes": notes
        }, default=str)
    finally:
        conn.close()


def get_market_note_status(status_filter: str = None) -> str:
    """
    Get market notes with their completion status and assignments.

    Args:
        status_filter: Optional filter by status (new, in_progress, on_hold, completed)

    Returns:
        JSON string with market notes, their status, and who they're assigned to
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        query = """
            SELECT
                mnc.id, mnc.visit_id, mnc.note_text, mnc.status, mnc.assigned_to,
                mnc.completed, mnc.completed_at,
                v."storeNbr", v.calendar_date
            FROM market_note_completions mnc
            JOIN store_visits v ON mnc.visit_id = v.id
        """
        params = []

        if status_filter:
            query += " WHERE LOWER(mnc.status) = LOWER(%s)"
            params.append(status_filter)

        query += " ORDER BY v.calendar_date DESC, mnc.id DESC LIMIT 50"

        cursor.execute(query, params)
        notes = cursor.fetchall()

        for note in notes:
            if note.get('calendar_date'):
                note['calendar_date'] = note['calendar_date'].isoformat()
            if note.get('completed_at'):
                note['completed_at'] = note['completed_at'].isoformat()

        cursor.close()
        return json.dumps(notes, default=str)
    finally:
        conn.close()


def get_market_note_updates(note_text: str = None) -> str:
    """
    Get updates/comments on market notes.

    Args:
        note_text: Optional filter to search for specific note text

    Returns:
        JSON string with market note updates and comments
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        query = """
            SELECT
                mnu.id, mnu.visit_id, mnu.note_text, mnu.update_text,
                mnu.created_by, mnu.created_at,
                v."storeNbr", v.calendar_date
            FROM market_note_updates mnu
            JOIN store_visits v ON mnu.visit_id = v.id
        """
        params = []

        if note_text:
            query += " WHERE LOWER(mnu.note_text) LIKE LOWER(%s)"
            params.append(f'%{note_text}%')

        query += " ORDER BY mnu.created_at DESC LIMIT 50"

        cursor.execute(query, params)
        updates = cursor.fetchall()

        for update in updates:
            if update.get('calendar_date'):
                update['calendar_date'] = update['calendar_date'].isoformat()
            if update.get('created_at'):
                update['created_at'] = update['created_at'].isoformat()

        cursor.close()
        return json.dumps(updates, default=str)
    finally:
        conn.close()


def get_gold_stars(week_date: str = None) -> str:
    """
    Get gold star focus areas and store completions.

    Args:
        week_date: Optional week start date (YYYY-MM-DD), defaults to current week

    Returns:
        JSON string with gold star notes and which stores have completed them
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        # Get the gold star week
        if week_date:
            cursor.execute("""
                SELECT * FROM gold_star_weeks WHERE week_start_date = %s
            """, (week_date,))
        else:
            cursor.execute("""
                SELECT * FROM gold_star_weeks ORDER BY week_start_date DESC LIMIT 1
            """)

        week = cursor.fetchone()
        if not week:
            return json.dumps({"error": "No gold star week found"})

        week_id = week['id']
        if week.get('week_start_date'):
            week['week_start_date'] = week['week_start_date'].isoformat()
        if week.get('updated_at'):
            week['updated_at'] = week['updated_at'].isoformat()

        # Get completions for this week
        cursor.execute("""
            SELECT store_nbr, note_number, completed, completed_at
            FROM gold_star_completions
            WHERE week_id = %s
            ORDER BY store_nbr, note_number
        """, (week_id,))
        completions = cursor.fetchall()

        for c in completions:
            if c.get('completed_at'):
                c['completed_at'] = c['completed_at'].isoformat()

        cursor.close()

        return json.dumps({
            "week": dict(week),
            "notes": [week.get('note_1'), week.get('note_2'), week.get('note_3')],
            "completions": [dict(c) for c in completions]
        }, default=str)
    finally:
        conn.close()


def get_champions() -> str:
    """
    Get all champions (team members) and their responsibilities.

    Returns:
        JSON string with champion names and their assigned responsibilities
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        cursor.execute("""
            SELECT id, name, responsibility, created_at
            FROM champions
            ORDER BY name
        """)
        champions = cursor.fetchall()

        for c in champions:
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()

        cursor.close()
        return json.dumps(champions, default=str)
    finally:
        conn.close()


def get_issues(status_filter: str = None, type_filter: str = None) -> str:
    """
    Get issues and feedback items.

    Args:
        status_filter: Optional filter by status (open, in_progress, resolved, closed)
        type_filter: Optional filter by type (issue, feedback)

    Returns:
        JSON string with issues/feedback and their details
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor)

        query = """
            SELECT id, type, title, description, status, created_at, updated_at
            FROM issues
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND LOWER(status) = LOWER(%s)"
            params.append(status_filter)

        if type_filter:
            query += " AND LOWER(type) = LOWER(%s)"
            params.append(type_filter)

        query += " ORDER BY created_at DESC LIMIT 50"

        cursor.execute(query, params)
        issues = cursor.fetchall()

        for issue in issues:
            if issue.get('created_at'):
                issue['created_at'] = issue['created_at'].isoformat()
            if issue.get('updated_at'):
                issue['updated_at'] = issue['updated_at'].isoformat()

        cursor.close()
        return json.dumps(issues, default=str)
    finally:
        conn.close()


# ADK Agent definition
def create_agent():
    """Create and return the ADK agent with all tools"""
    try:
        from google.adk.agents import Agent

        agent = Agent(
            model="gemini-2.0-flash",
            name="store_visit_analyst",
            description="An AI assistant that helps analyze store visit data, trends, and insights.",
            instruction="""You are a helpful assistant for analyzing store visit data for a retail district manager.

You have access to a database of store visits that includes:
- Visit dates and store numbers
- Ratings (Green, Yellow, Red)
- Sales metrics (comps, indexes)
- Operational metrics (vizpick, overstock, FTPR, etc.)
- Notes categorized as: store observations, market notes, good notes, improvement areas

When answering questions:
1. Use the appropriate tool to query the data
2. Provide clear, actionable insights
3. Highlight trends or concerns when relevant
4. Be specific with numbers and dates
5. If data is missing, say so rather than guessing

Common metrics explained:
- Sales Comp: Year-over-year sales comparison (positive is good)
- VizPick: Inventory visibility score (higher is better)
- FTPR: First Time Pick Rate (higher is better)
- Overstock: Count of overstock items (lower is better)
""",
            tools=[
                search_visits,
                get_visit_details,
                analyze_trends,
                compare_stores,
                search_notes,
                get_summary_stats,
                get_market_insights
            ]
        )
        return agent
    except ImportError:
        return None


# For standalone testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Test the tools directly
    print("Testing search_visits...")
    print(search_visits("1234", 3))

    print("\nTesting get_summary_stats...")
    print(get_summary_stats())
