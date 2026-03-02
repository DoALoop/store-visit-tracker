"""
JaxAI Tools Package
Domain-organized tools for the JaxAI chatbot agent.
"""

from tools.visits import search_visits, get_visit_details, analyze_trends, compare_stores
from tools.notes import search_notes, get_market_insights, get_market_note_status, get_market_note_updates
from tools.team import get_champions, get_mentees, get_contacts
from tools.tracking import get_gold_stars, get_enablers, get_issues, get_tasks, get_user_notes
from tools.summary import get_summary_stats
from tools.store_info import get_store_information

# Action tools (write operations)
from tools.actions import (
    # Gold star actions
    mark_gold_star_complete,
    save_gold_star_notes,
    # Contact actions
    create_contact,
    delete_contact,
    # Task actions
    create_task,
    update_task_status,
    delete_task,
    # Market note actions
    update_market_note_status,
    assign_market_note,
    add_market_note_comment,
    mark_market_note_complete,
    # Champion actions
    create_champion,
    delete_champion,
    # Mentee actions
    create_mentee,
    delete_mentee,
    # Enabler actions
    mark_enabler_complete,
    create_enabler,
    # Issue actions
    create_issue,
)

# Query tools (read operations)
QUERY_TOOLS = [
    # Visits domain
    search_visits,
    get_visit_details,
    analyze_trends,
    compare_stores,
    # Notes domain
    search_notes,
    get_market_insights,
    get_market_note_status,
    get_market_note_updates,
    # Team domain
    get_champions,
    get_mentees,
    get_contacts,
    # Tracking domain
    get_gold_stars,
    get_enablers,
    get_issues,
    get_tasks,
    get_user_notes,
    # Summary
    get_summary_stats,
    # Store Info
    get_store_information,
]

# Action tools (write operations)
ACTION_TOOLS = [
    # Gold star actions
    mark_gold_star_complete,
    save_gold_star_notes,
    # Contact actions
    create_contact,
    delete_contact,
    # Task actions
    create_task,
    update_task_status,
    delete_task,
    # Market note actions
    update_market_note_status,
    assign_market_note,
    add_market_note_comment,
    mark_market_note_complete,
    # Champion actions
    create_champion,
    delete_champion,
    # Mentee actions
    create_mentee,
    delete_mentee,
    # Enabler actions
    mark_enabler_complete,
    create_enabler,
    # Issue actions
    create_issue,
]

# All tools available for ADK agent registration
ALL_TOOLS = QUERY_TOOLS + ACTION_TOOLS

__all__ = [
    # Query tools
    'search_visits', 'get_visit_details', 'analyze_trends', 'compare_stores',
    'search_notes', 'get_market_insights', 'get_market_note_status', 'get_market_note_updates',
    'get_champions', 'get_mentees', 'get_contacts',
    'get_gold_stars', 'get_enablers', 'get_issues', 'get_tasks', 'get_user_notes',
    'get_summary_stats',
    'get_store_information',
    # Action tools
    'mark_gold_star_complete', 'save_gold_star_notes',
    'create_contact', 'delete_contact',
    'create_task', 'update_task_status', 'delete_task',
    'update_market_note_status', 'assign_market_note', 'add_market_note_comment', 'mark_market_note_complete',
    'create_champion', 'delete_champion',
    'create_mentee', 'delete_mentee',
    'mark_enabler_complete', 'create_enabler',
    'create_issue',
    # Collections
    'QUERY_TOOLS', 'ACTION_TOOLS', 'ALL_TOOLS',
]
