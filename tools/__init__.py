"""
JaxAI Tools Package
Domain-organized tools for the JaxAI chatbot agent.
"""

from tools.visits import search_visits, get_visit_details, analyze_trends, compare_stores
from tools.notes import search_notes, get_market_insights, get_market_note_status, get_market_note_updates
from tools.team import get_champions, get_mentees, get_contacts
from tools.tracking import get_gold_stars, get_enablers, get_issues, get_tasks, get_user_notes
from tools.summary import get_summary_stats

# All tools available for ADK agent registration
ALL_TOOLS = [
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
]

__all__ = [
    'search_visits', 'get_visit_details', 'analyze_trends', 'compare_stores',
    'search_notes', 'get_market_insights', 'get_market_note_status', 'get_market_note_updates',
    'get_champions', 'get_mentees', 'get_contacts',
    'get_gold_stars', 'get_enablers', 'get_issues', 'get_tasks', 'get_user_notes',
    'get_summary_stats',
    'ALL_TOOLS',
]
