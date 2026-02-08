"""
Action Tools
Tools for performing write operations: gold stars, contacts, tasks, market notes, etc.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from psycopg2.extras import RealDictCursor

from tools.db import get_db_connection, release_db_connection
from tools.fiscal import get_fiscal_week_number, get_monday_from_fiscal_week


# ===================== GOLD STAR ACTIONS =====================

def mark_gold_star_complete(store_nbr: str, note_number: int, completed: bool = True, week_id: int = None) -> str:
    """
    Mark a gold star as complete or incomplete for a store.

    Args:
        store_nbr: The store number (e.g., "1234")
        note_number: Which gold star note (1, 2, or 3)
        completed: True to mark complete, False to mark incomplete
        week_id: Optional week ID, defaults to current week

    Returns:
        JSON string with success status and details
    """
    if note_number not in [1, 2, 3]:
        return json.dumps({"success": False, "error": "note_number must be 1, 2, or 3"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get the current week if not specified
        if not week_id:
            cursor.execute("SELECT id, note_1, note_2, note_3 FROM gold_star_weeks ORDER BY week_start_date DESC LIMIT 1")
            week = cursor.fetchone()
            if not week:
                return json.dumps({"success": False, "error": "No gold star week found"})
            week_id = week['id']
            note_text = week.get(f'note_{note_number}', f'Gold Star #{note_number}')
        else:
            cursor.execute("SELECT note_1, note_2, note_3 FROM gold_star_weeks WHERE id = %s", (week_id,))
            week = cursor.fetchone()
            note_text = week.get(f'note_{note_number}', f'Gold Star #{note_number}') if week else f'Gold Star #{note_number}'

        # Upsert the completion
        cursor.execute("""
            INSERT INTO gold_star_completions (week_id, store_nbr, note_number, completed, completed_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (week_id, store_nbr, note_number)
            DO UPDATE SET completed = EXCLUDED.completed, completed_at = EXCLUDED.completed_at
        """, (week_id, store_nbr, note_number, completed, datetime.now() if completed else None))

        conn.commit()
        cursor.close()

        action = "marked complete" if completed else "marked incomplete"
        return json.dumps({
            "success": True,
            "message": f"Gold Star #{note_number} {action} for store {store_nbr}",
            "store_nbr": store_nbr,
            "note_number": note_number,
            "note_text": note_text,
            "completed": completed
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def save_gold_star_notes(note_1: str, note_2: str, note_3: str) -> str:
    """
    Update the gold star notes for the current week.

    Args:
        note_1: Text for gold star note 1
        note_2: Text for gold star note 2
        note_3: Text for gold star note 3

    Returns:
        JSON string with success status and the updated notes
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get current week
        cursor.execute("SELECT id FROM gold_star_weeks ORDER BY week_start_date DESC LIMIT 1")
        week = cursor.fetchone()

        if not week:
            return json.dumps({"success": False, "error": "No gold star week found"})

        cursor.execute("""
            UPDATE gold_star_weeks
            SET note_1 = %s, note_2 = %s, note_3 = %s, updated_at = NOW()
            WHERE id = %s
        """, (note_1, note_2, note_3, week['id']))

        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": "Gold star notes updated",
            "notes": [note_1, note_2, note_3]
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== CONTACT ACTIONS =====================

def create_contact(name: str, title: str = None, department: str = None,
                   reports_to: str = None, phone: str = None, email: str = None,
                   notes: str = None) -> str:
    """
    Create a new contact/person of interest.

    Args:
        name: Contact's full name (required)
        title: Job title or role
        department: Department or area (e.g., "Meat", "OGP", "Produce")
        reports_to: Who they report to
        phone: Phone number
        email: Email address
        notes: Additional notes

    Returns:
        JSON string with success status and the created contact
    """
    if not name or not name.strip():
        return json.dumps({"success": False, "error": "Name is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO contacts (name, title, department, reports_to, phone, email, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, name, title, department, reports_to, phone, email, notes
        """, (name.strip(), title, department, reports_to, phone, email, notes))

        contact = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Contact '{name}' created successfully",
            "contact": dict(contact)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def delete_contact(contact_id: int = None, name: str = None) -> str:
    """
    Delete a contact by ID or name.

    Args:
        contact_id: The contact's ID
        name: The contact's name (used if ID not provided)

    Returns:
        JSON string with success status
    """
    if not contact_id and not name:
        return json.dumps({"success": False, "error": "Either contact_id or name is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if contact_id:
            cursor.execute("DELETE FROM contacts WHERE id = %s RETURNING name", (contact_id,))
        else:
            cursor.execute("DELETE FROM contacts WHERE LOWER(name) = LOWER(%s) RETURNING name", (name,))

        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()

        if deleted:
            return json.dumps({
                "success": True,
                "message": f"Contact '{deleted['name']}' deleted"
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Contact not found"
            })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== TASK ACTIONS =====================

def create_task(content: str, priority: int = 0, assigned_to: str = None,
                due_date: str = None, store_number: str = None,
                list_name: str = "Inbox", notes: str = None) -> str:
    """
    Create a new task.

    Args:
        content: Task description (required)
        priority: Priority level (0=none, 1=low, 2=medium, 3=high)
        assigned_to: Person assigned to the task
        due_date: Due date in YYYY-MM-DD format
        store_number: Associated store number
        list_name: Task list name (default "Inbox")
        notes: Additional notes

    Returns:
        JSON string with success status and the created task
    """
    if not content or not content.strip():
        return json.dumps({"success": False, "error": "Task content is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO tasks (content, status, priority, assigned_to, due_date, store_number, list_name, notes, created_at)
            VALUES (%s, 'new', %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, content, status, priority, assigned_to, due_date, store_number, list_name
        """, (content.strip(), priority, assigned_to, due_date, store_number, list_name, notes))

        task = cursor.fetchone()
        conn.commit()
        cursor.close()

        # Format due_date for display
        if task.get('due_date'):
            task['due_date'] = task['due_date'].isoformat()

        return json.dumps({
            "success": True,
            "message": f"Task created: {content[:50]}...",
            "task": dict(task)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def update_task_status(task_id: int, status: str) -> str:
    """
    Update a task's status.

    Args:
        task_id: The task ID
        status: New status (new, in_progress, stalled, completed)

    Returns:
        JSON string with success status and updated task
    """
    valid_statuses = ['new', 'in_progress', 'stalled', 'completed']
    if status.lower() not in valid_statuses:
        return json.dumps({"success": False, "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        completed_at = datetime.now() if status.lower() == 'completed' else None

        cursor.execute("""
            UPDATE tasks
            SET status = %s, updated_at = NOW(), completed_at = %s
            WHERE id = %s
            RETURNING id, content, status, priority
        """, (status.lower(), completed_at, task_id))

        task = cursor.fetchone()
        conn.commit()
        cursor.close()

        if task:
            return json.dumps({
                "success": True,
                "message": f"Task #{task_id} status updated to '{status}'",
                "task": dict(task)
            })
        else:
            return json.dumps({"success": False, "error": f"Task #{task_id} not found"})
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def delete_task(task_id: int) -> str:
    """
    Delete a task.

    Args:
        task_id: The task ID to delete

    Returns:
        JSON string with success status
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("DELETE FROM tasks WHERE id = %s RETURNING content", (task_id,))
        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()

        if deleted:
            return json.dumps({
                "success": True,
                "message": f"Task #{task_id} deleted"
            })
        else:
            return json.dumps({"success": False, "error": f"Task #{task_id} not found"})
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== MARKET NOTE ACTIONS =====================

def update_market_note_status(visit_id: int, note_text: str, status: str) -> str:
    """
    Update a market note's status.

    Args:
        visit_id: The visit ID the note belongs to
        note_text: The note text (used to identify the note)
        status: New status (new, in_progress, stalled, completed)

    Returns:
        JSON string with success status
    """
    valid_statuses = ['new', 'in_progress', 'stalled', 'completed']
    if status.lower() not in valid_statuses:
        return json.dumps({"success": False, "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        completed = status.lower() == 'completed'

        # Update the note in market_note_completions table
        cursor.execute("""
            INSERT INTO market_note_completions (visit_id, note_text, completed, status, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (visit_id, note_text)
            DO UPDATE SET completed = EXCLUDED.completed, status = EXCLUDED.status, updated_at = NOW()
        """, (visit_id, note_text, completed, status.lower()))

        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Market note status updated to '{status}'",
            "visit_id": visit_id,
            "status": status.lower()
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def assign_market_note(visit_id: int, note_text: str, assigned_to: str) -> str:
    """
    Assign a market note to a person.

    Args:
        visit_id: The visit ID the note belongs to
        note_text: The note text (used to identify the note)
        assigned_to: Person to assign the note to

    Returns:
        JSON string with success status
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO market_note_completions (visit_id, note_text, assigned_to, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (visit_id, note_text)
            DO UPDATE SET assigned_to = EXCLUDED.assigned_to, updated_at = NOW()
        """, (visit_id, note_text, assigned_to))

        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Market note assigned to {assigned_to}",
            "visit_id": visit_id,
            "assigned_to": assigned_to
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def add_market_note_comment(visit_id: int, note_text: str, comment: str) -> str:
    """
    Add a comment/update to a market note.

    Args:
        visit_id: The visit ID the note belongs to
        note_text: The note text (used to identify the note)
        comment: The comment/update text to add

    Returns:
        JSON string with success status
    """
    if not comment or not comment.strip():
        return json.dumps({"success": False, "error": "Comment text is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO market_note_updates (visit_id, note_text, text, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
        """, (visit_id, note_text, comment.strip()))

        update = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Comment added to market note",
            "update_id": update['id'],
            "comment": comment[:50] + "..." if len(comment) > 50 else comment
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def mark_market_note_complete(visit_id: int, note_text: str) -> str:
    """
    Mark a market note as completed.

    Args:
        visit_id: The visit ID the note belongs to
        note_text: The note text (used to identify the note)

    Returns:
        JSON string with success status
    """
    return update_market_note_status(visit_id, note_text, 'completed')


# ===================== CHAMPION ACTIONS =====================

def create_champion(name: str, responsibility: str) -> str:
    """
    Create a new champion.

    Args:
        name: Champion's name
        responsibility: Area of responsibility

    Returns:
        JSON string with success status and the created champion
    """
    if not name or not name.strip():
        return json.dumps({"success": False, "error": "Name is required"})
    if not responsibility or not responsibility.strip():
        return json.dumps({"success": False, "error": "Responsibility is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO champions (name, responsibility, created_at)
            VALUES (%s, %s, NOW())
            RETURNING id, name, responsibility
        """, (name.strip(), responsibility.strip()))

        champion = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Champion '{name}' created for {responsibility}",
            "champion": dict(champion)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def delete_champion(champion_id: int = None, name: str = None) -> str:
    """
    Delete a champion by ID or name.

    Args:
        champion_id: The champion's ID
        name: The champion's name (used if ID not provided)

    Returns:
        JSON string with success status
    """
    if not champion_id and not name:
        return json.dumps({"success": False, "error": "Either champion_id or name is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if champion_id:
            cursor.execute("DELETE FROM champions WHERE id = %s RETURNING name", (champion_id,))
        else:
            cursor.execute("DELETE FROM champions WHERE LOWER(name) = LOWER(%s) RETURNING name", (name,))

        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()

        if deleted:
            return json.dumps({
                "success": True,
                "message": f"Champion '{deleted['name']}' deleted"
            })
        else:
            return json.dumps({"success": False, "error": "Champion not found"})
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== MENTEE ACTIONS =====================

def create_mentee(name: str, store_nbr: str = None, position: str = None,
                  cell_number: str = None, notes: str = None) -> str:
    """
    Create a new mentee.

    Args:
        name: Mentee's name (required)
        store_nbr: Store number
        position: Job position
        cell_number: Cell phone number
        notes: Additional notes

    Returns:
        JSON string with success status and the created mentee
    """
    if not name or not name.strip():
        return json.dumps({"success": False, "error": "Name is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO mentees (name, store_nbr, position, cell_number, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id, name, store_nbr, position, cell_number, notes
        """, (name.strip(), store_nbr, position, cell_number, notes))

        mentee = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Mentee '{name}' added to your circle",
            "mentee": dict(mentee)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def delete_mentee(mentee_id: int = None, name: str = None) -> str:
    """
    Delete a mentee by ID or name.

    Args:
        mentee_id: The mentee's ID
        name: The mentee's name (used if ID not provided)

    Returns:
        JSON string with success status
    """
    if not mentee_id and not name:
        return json.dumps({"success": False, "error": "Either mentee_id or name is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if mentee_id:
            cursor.execute("DELETE FROM mentees WHERE id = %s RETURNING name", (mentee_id,))
        else:
            cursor.execute("DELETE FROM mentees WHERE LOWER(name) = LOWER(%s) RETURNING name", (name,))

        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()

        if deleted:
            return json.dumps({
                "success": True,
                "message": f"Mentee '{deleted['name']}' removed from your circle"
            })
        else:
            return json.dumps({"success": False, "error": "Mentee not found"})
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== ENABLER ACTIONS =====================

def mark_enabler_complete(enabler_id: int, store_nbr: str, completed: bool = True) -> str:
    """
    Mark an enabler as complete for a specific store.

    Args:
        enabler_id: The enabler ID
        store_nbr: The store number
        completed: True to mark complete, False to mark incomplete

    Returns:
        JSON string with success status
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get the enabler title for the response
        cursor.execute("SELECT title FROM enablers WHERE id = %s", (enabler_id,))
        enabler = cursor.fetchone()
        if not enabler:
            return json.dumps({"success": False, "error": f"Enabler #{enabler_id} not found"})

        cursor.execute("""
            INSERT INTO enabler_completions (enabler_id, store_nbr, completed, completed_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (enabler_id, store_nbr)
            DO UPDATE SET completed = EXCLUDED.completed, completed_at = EXCLUDED.completed_at
        """, (enabler_id, store_nbr, completed, datetime.now() if completed else None))

        conn.commit()
        cursor.close()

        action = "marked complete" if completed else "marked incomplete"
        return json.dumps({
            "success": True,
            "message": f"Enabler '{enabler['title']}' {action} for store {store_nbr}",
            "enabler_id": enabler_id,
            "store_nbr": store_nbr,
            "completed": completed
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


def create_enabler(title: str, description: str = None, source: str = None) -> str:
    """
    Create a new enabler (tip/trick/way of working).

    Args:
        title: Enabler title (required)
        description: Detailed description
        source: Source of the enabler

    Returns:
        JSON string with success status and the created enabler
    """
    if not title or not title.strip():
        return json.dumps({"success": False, "error": "Title is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO enablers (title, description, source, status, created_at)
            VALUES (%s, %s, %s, 'idea', NOW())
            RETURNING id, title, description, source, status
        """, (title.strip(), description, source))

        enabler = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"Enabler '{title}' created",
            "enabler": dict(enabler)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)


# ===================== ISSUE ACTIONS =====================

def create_issue(issue_type: str, title: str, description: str = None) -> str:
    """
    Create a new issue or feedback.

    Args:
        issue_type: Type (feature, bug, feedback)
        title: Issue title (required)
        description: Detailed description

    Returns:
        JSON string with success status and the created issue
    """
    valid_types = ['feature', 'bug', 'feedback']
    if issue_type.lower() not in valid_types:
        return json.dumps({"success": False, "error": f"Invalid type. Must be one of: {', '.join(valid_types)}"})

    if not title or not title.strip():
        return json.dumps({"success": False, "error": "Title is required"})

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            INSERT INTO issues (type, title, description, status, created_at)
            VALUES (%s, %s, %s, 'open', NOW())
            RETURNING id, type, title, status
        """, (issue_type.lower(), title.strip(), description))

        issue = cursor.fetchone()
        conn.commit()
        cursor.close()

        return json.dumps({
            "success": True,
            "message": f"{issue_type.capitalize()} '{title}' logged",
            "issue": dict(issue)
        })
    except Exception as e:
        conn.rollback()
        return json.dumps({"success": False, "error": str(e)})
    finally:
        release_db_connection(conn)
