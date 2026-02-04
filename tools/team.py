"""
Team Tools
Tools for managing champions, mentees, and contacts.
"""

import json
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection


def get_champions() -> str:
    """
    Get all champions (team members) and their responsibilities.

    Returns:
        JSON string with champion names and their assigned responsibilities
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        release_db_connection(conn)


def get_mentees(store_nbr: Optional[str] = None) -> str:
    """
    Get mentee circle members.

    Args:
        store_nbr: Optional filter by store number

    Returns:
        JSON string with mentee names, stores, positions, and contact info
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, name, store_nbr, position, cell_number, notes, created_at
            FROM mentees
            WHERE 1=1
        """
        params = []

        if store_nbr:
            query += " AND store_nbr = %s"
            params.append(store_nbr)

        query += " ORDER BY name"

        cursor.execute(query, params)
        mentees = cursor.fetchall()

        for m in mentees:
            if m.get('created_at'):
                m['created_at'] = m['created_at'].isoformat()

        cursor.close()
        return json.dumps(mentees, default=str)
    finally:
        release_db_connection(conn)


def get_contacts(search_term: Optional[str] = None, department: Optional[str] = None) -> str:
    """
    Get contacts list - people of interest to reach out to.

    Args:
        search_term: Optional search term to filter by name, title, or department
        department: Optional filter by department/what they oversee

    Returns:
        JSON string with contact names, titles, departments, who they report to, and contact info
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, name, title, department, reports_to, phone, email, notes, created_at
            FROM contacts
            WHERE 1=1
        """
        params = []

        if search_term:
            query += """ AND (LOWER(name) LIKE LOWER(%s)
                         OR LOWER(title) LIKE LOWER(%s)
                         OR LOWER(department) LIKE LOWER(%s)
                         OR LOWER(reports_to) LIKE LOWER(%s)
                         OR LOWER(notes) LIKE LOWER(%s))"""
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 5)

        if department:
            query += " AND LOWER(department) LIKE LOWER(%s)"
            params.append(f"%{department}%")

        query += " ORDER BY name"

        cursor.execute(query, params)
        contacts = cursor.fetchall()

        for c in contacts:
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()

        cursor.close()
        return json.dumps(contacts, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        release_db_connection(conn)
