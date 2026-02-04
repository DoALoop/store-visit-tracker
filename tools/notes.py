"""
Notes Tools
Tools for searching notes and managing market insights.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection


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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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

        results.sort(key=lambda x: x.get('calendar_date', ''), reverse=True)
        return json.dumps(results[:limit], default=str)
    finally:
        release_db_connection(conn)


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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        release_db_connection(conn)


def get_market_note_status(status_filter: Optional[str] = None) -> str:
    """
    Get ALL market notes with their completion status and assignments.

    Args:
        status_filter: Optional filter by status (new, in_progress, on_hold, completed)

    Returns:
        JSON string with market notes, their status, and who they're assigned to
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                smn.id, smn.visit_id, smn.note_text,
                COALESCE(mnc.status, 'new') as status,
                mnc.assigned_to,
                COALESCE(mnc.completed, false) as completed,
                mnc.completed_at,
                v."storeNbr", v.calendar_date
            FROM store_market_notes smn
            JOIN store_visits v ON smn.visit_id = v.id
            LEFT JOIN market_note_completions mnc
                ON smn.visit_id = mnc.visit_id AND smn.note_text = mnc.note_text
        """
        params = []

        if status_filter and status_filter.lower() == 'completed':
            query += " WHERE COALESCE(mnc.status, 'new') = 'completed'"
        elif status_filter:
            query += " WHERE COALESCE(mnc.status, 'new') = %s"
            params.append(status_filter)
        else:
            query += " WHERE COALESCE(mnc.status, 'new') != 'completed'"

        query += " ORDER BY v.calendar_date DESC, smn.id DESC LIMIT 100"

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
        release_db_connection(conn)


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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        release_db_connection(conn)
