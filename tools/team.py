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


def _normalize_search_term(term: str) -> list:
    """
    Normalize search term to handle plurals, common variations, and retail terminology.
    Returns a list of search variations to try.
    """
    if not term:
        return []

    term = term.lower().strip()
    variations = [term]

    # Handle common plural endings
    if term.endswith('ies'):
        variations.append(term[:-3] + 'y')  # bakeries -> bakery
    elif term.endswith('es'):
        variations.append(term[:-2])  # produces -> produc (catches produce)
        variations.append(term[:-1])  # boxes -> boxe (fallback)
    elif term.endswith('s') and len(term) > 2:
        variations.append(term[:-1])  # meats -> meat

    # Also try adding 's' if singular
    if not term.endswith('s'):
        variations.append(term + 's')

    # Common retail department aliases
    retail_aliases = {
        'meat': ['meat', 'meats', 'butcher', 'protein'],
        'meats': ['meat', 'meats', 'butcher', 'protein'],
        'produce': ['produce', 'fruits', 'vegetables', 'fresh'],
        'deli': ['deli', 'delicatessen', 'prepared foods'],
        'bakery': ['bakery', 'bread', 'baked goods'],
        'dairy': ['dairy', 'milk', 'cheese', 'refrigerated'],
        'frozen': ['frozen', 'freezer', 'ice cream'],
        'grocery': ['grocery', 'center store', 'dry grocery'],
        'hba': ['hba', 'health', 'beauty', 'pharmacy', 'otc'],
        'gm': ['gm', 'general merchandise', 'hardlines'],
        'apparel': ['apparel', 'clothing', 'softlines', 'fashion'],
        'electronics': ['electronics', 'wireless', 'photo', 'entertainment'],
        'sporting': ['sporting', 'sports', 'outdoor', 'fitness'],
        'automotive': ['automotive', 'auto', 'tires', 'tle'],
        'garden': ['garden', 'lawn', 'outdoor living', 'seasonal'],
        'pets': ['pets', 'pet', 'animal'],
        'baby': ['baby', 'infant', 'kids'],
        'toys': ['toys', 'toy', 'games'],
        'home': ['home', 'housewares', 'domestics', 'furniture'],
        'pharmacy': ['pharmacy', 'rx', 'pharmacist'],
        'optical': ['optical', 'vision', 'glasses'],
        'acc': ['acc', 'auto care', 'automotive'],
        'ogp': ['ogp', 'online grocery', 'pickup', 'delivery', 'digital'],
        'frontend': ['frontend', 'front end', 'cashier', 'self checkout', 'sco'],
        'claims': ['claims', 'receiving', 'backroom'],
        'inventory': ['inventory', 'inv', 'counts', 'on hand'],
        'fresh': ['fresh', 'perishables', 'produce', 'meat', 'deli', 'bakery'],
        'cap': ['cap', 'stocking', 'freight'],
        'ap': ['ap', 'asset protection', 'security', 'loss prevention'],
        'people': ['people', 'hr', 'human resources', 'personnel', 'associate'],
        'ops': ['ops', 'operations', 'store ops'],
        'coach': ['coach', 'team lead', 'tl', 'supervisor'],
        'manager': ['manager', 'mgr', 'asm', 'store manager', 'sm'],
    }

    # Add aliases if term matches
    for key, aliases in retail_aliases.items():
        if term in aliases or any(term in alias for alias in aliases):
            variations.extend(aliases)

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)

    return unique_variations


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
            # Get all search variations (handles plurals, aliases)
            search_variations = _normalize_search_term(search_term)

            # Build OR conditions for each variation
            or_conditions = []
            for variation in search_variations:
                or_conditions.append("""(LOWER(name) LIKE LOWER(%s)
                                     OR LOWER(title) LIKE LOWER(%s)
                                     OR LOWER(department) LIKE LOWER(%s)
                                     OR LOWER(reports_to) LIKE LOWER(%s)
                                     OR LOWER(notes) LIKE LOWER(%s))""")
                search_pattern = f"%{variation}%"
                params.extend([search_pattern] * 5)

            if or_conditions:
                query += " AND (" + " OR ".join(or_conditions) + ")"

        if department:
            dept_variations = _normalize_search_term(department)
            dept_conditions = []
            for variation in dept_variations:
                dept_conditions.append("LOWER(department) LIKE LOWER(%s)")
                params.append(f"%{variation}%")
            if dept_conditions:
                query += " AND (" + " OR ".join(dept_conditions) + ")"

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
