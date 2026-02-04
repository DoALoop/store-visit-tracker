"""
Tracking Tools
Tools for gold stars, enablers, issues, tasks, and user notes.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection
from tools.fiscal import get_fiscal_week_number, get_monday_from_fiscal_week


def get_gold_stars(week_date: str = None, week_number: int = None) -> str:
    """
    Get gold star focus areas and store completions.

    Args:
        week_date: Optional week start date (YYYY-MM-DD), defaults to current week
        week_number: Optional Walmart fiscal week number (e.g., 51 for week 51)

    Returns:
        JSON string with gold star notes, week number, and which stores have completed them
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Convert week_number to week_date if provided
        if week_number and not week_date:
            week_monday = get_monday_from_fiscal_week(week_number)
            week_saturday = week_monday - timedelta(days=2)
            week_date = week_saturday.isoformat()

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
            return json.dumps({"error": f"No gold star data found for week {week_number}" if week_number else "No gold star week found"})

        week_id = week['id']

        # Calculate the week number from the week_start_date
        week_start = week.get('week_start_date')
        calculated_week_number = None
        if week_start:
            if isinstance(week_start, str):
                week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
            calculated_week_number = get_fiscal_week_number(week_start)
            week['week_start_date'] = week_start.isoformat() if hasattr(week_start, 'isoformat') else str(week_start)

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
            "week_number": calculated_week_number,
            "notes": [week.get('note_1'), week.get('note_2'), week.get('note_3')],
            "completions": [dict(c) for c in completions]
        }, default=str)
    finally:
        release_db_connection(conn)


def get_enablers(status_filter: Optional[str] = None, week_number: Optional[int] = None) -> str:
    """
    Get enablers (tips/tricks/ways of working).

    Args:
        status_filter: Optional filter by status (idea, slide_made, presented)
        week_number: Optional filter by Walmart week number

    Returns:
        JSON string with enablers, their status, and store completion counts
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT e.id, e.title, e.description, e.source, e.status, e.week_date,
                   e.created_at, e.updated_at,
                   COUNT(ec.id) FILTER (WHERE ec.completed = true) as completed_count,
                   COUNT(ec.id) as total_tracked
            FROM enablers e
            LEFT JOIN enabler_completions ec ON e.id = ec.enabler_id
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND LOWER(e.status) = LOWER(%s)"
            params.append(status_filter)

        query += """
            GROUP BY e.id, e.title, e.description, e.source, e.status, e.week_date, e.created_at, e.updated_at
            ORDER BY e.week_date DESC NULLS LAST, e.created_at DESC
        """

        cursor.execute(query, params)
        enablers = cursor.fetchall()

        for e in enablers:
            if e.get('created_at'):
                e['created_at'] = e['created_at'].isoformat()
            if e.get('updated_at'):
                e['updated_at'] = e['updated_at'].isoformat()
            if e.get('week_date'):
                e['week_date'] = e['week_date'].isoformat()

        cursor.close()
        return json.dumps(enablers, default=str)
    finally:
        release_db_connection(conn)


def get_issues(status_filter: Optional[str] = None, type_filter: Optional[str] = None) -> str:
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        release_db_connection(conn)


def get_tasks(status_filter: Optional[str] = None, assigned_to: Optional[str] = None,
              store_number: Optional[str] = None) -> str:
    """
    Get standalone tasks.

    Args:
        status_filter: Optional filter by status (new, in_progress, stalled, completed)
        assigned_to: Optional filter by assignee name
        store_number: Optional filter by store number

    Returns:
        JSON string with tasks including status, priority, assignments, and due dates
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, content, status, priority, assigned_to, due_date,
                   store_number, list_name, notes, created_at, updated_at, completed_at
            FROM tasks
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND LOWER(status) = LOWER(%s)"
            params.append(status_filter)

        if assigned_to:
            query += " AND LOWER(assigned_to) LIKE LOWER(%s)"
            params.append(f'%{assigned_to}%')

        if store_number:
            query += " AND store_number = %s"
            params.append(store_number)

        query += " ORDER BY priority DESC, due_date ASC NULLS LAST, created_at DESC LIMIT 50"

        cursor.execute(query, params)
        tasks = cursor.fetchall()

        for t in tasks:
            if t.get('created_at'):
                t['created_at'] = t['created_at'].isoformat()
            if t.get('updated_at'):
                t['updated_at'] = t['updated_at'].isoformat()
            if t.get('completed_at'):
                t['completed_at'] = t['completed_at'].isoformat()
            if t.get('due_date'):
                t['due_date'] = t['due_date'].isoformat()

        cursor.close()
        return json.dumps(tasks, default=str)
    finally:
        release_db_connection(conn)


def get_user_notes(search_query: Optional[str] = None, folder_path: Optional[str] = None) -> str:
    """
    Get user notes from the notes module.

    Args:
        search_query: Optional search query for note content
        folder_path: Optional filter by folder path

    Returns:
        JSON string with notes including title, content preview, tags, and task counts
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT n.id, n.title,
                   LEFT(n.content, 200) as content_preview,
                   n.folder_path, n.is_pinned, n.is_daily_note, n.daily_date,
                   n.store_number, n.created_at, n.updated_at,
                   COUNT(DISTINCT nt.id) as task_count,
                   COUNT(DISTINCT nt.id) FILTER (WHERE nt.is_completed = true) as completed_task_count
            FROM notes n
            LEFT JOIN note_tasks nt ON n.id = nt.note_id
            WHERE n.deleted_at IS NULL
        """
        params = []

        if search_query:
            query += " AND (LOWER(n.title) LIKE LOWER(%s) OR LOWER(n.content) LIKE LOWER(%s))"
            params.extend([f'%{search_query}%', f'%{search_query}%'])

        if folder_path:
            query += " AND n.folder_path = %s"
            params.append(folder_path)

        query += """
            GROUP BY n.id, n.title, n.content, n.folder_path, n.is_pinned,
                     n.is_daily_note, n.daily_date, n.store_number, n.created_at, n.updated_at
            ORDER BY n.is_pinned DESC, n.updated_at DESC
            LIMIT 30
        """

        cursor.execute(query, params)
        notes = cursor.fetchall()

        for note in notes:
            if note.get('created_at'):
                note['created_at'] = note['created_at'].isoformat()
            if note.get('updated_at'):
                note['updated_at'] = note['updated_at'].isoformat()
            if note.get('daily_date'):
                note['daily_date'] = note['daily_date'].isoformat()

        cursor.close()
        return json.dumps(notes, default=str)
    finally:
        release_db_connection(conn)
