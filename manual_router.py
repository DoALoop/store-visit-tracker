"""
Manual Router - Regex-based fallback routing for JaxAI
Extracted from main.py chat() function for use when LLM is unavailable.
"""

import re
from typing import Tuple, Dict, Any, Optional


class ManualRouter:
    """Regex-based routing fallback when LLM unavailable"""

    def __init__(self):
        # Contact detection patterns - order matters (more specific first)
        self.contacts_patterns = [
            # "who has/handles/oversees X" patterns
            r'who\s+(?:has|handles?|oversees?|owns?|manages?|works?\s+on|is\s+over|is\s+responsible\s+for|covers?|runs?|leads?)\s+(.+?)(?:\?|$)',
            # "contact/person for X"
            r'(?:contact|person|guy|point\s+of\s+contact|poc)\s+for\s+(.+?)(?:\?|$)',
            # "who do I call/contact for X"
            r'who\s+(?:do\s+i|should\s+i|can\s+i|to)\s+(?:call|contact|reach|talk\s+to|speak\s+with|ask)\s+(?:for|about|regarding|on)?\s*(.+?)(?:\?|$)',
            # "who can help with X"
            r'who\s+(?:can\s+help\s+with|knows\s+about|deals\s+with|works\s+with)\s+(.+?)(?:\?|$)',
            # "who is over X" / "who is the X person"
            r'who\s+is\s+(?:over\s+|the\s+)?(.+?)(?:\s+person|\s+guy|\s+contact|\s+lead)?(?:\?|$)',
            # "X contact" or "X person"
            r'(.+?)\s+(?:contact|person|guy|lead|manager)(?:\?|$)',
            # "get me X" / "find X contact"
            r'(?:get|find|show)\s+(?:me\s+)?(?:the\s+)?(.+?)\s+(?:contact|person|info)(?:\?|$)',
        ]

    def route(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Route message to appropriate tool based on regex patterns.

        Returns:
            Tuple of (tool_name, kwargs)
        """
        message_lower = message.lower()

        # Extract common parameters
        numbers = re.findall(r'\b\d{4,5}\b', message)
        rating_filter = self._extract_rating(message_lower)
        status_filter = self._extract_status(message_lower)

        # Priority-ordered routing rules

        # Contacts
        contacts_match = self._match_contacts(message_lower)
        list_contacts = any(kw in message_lower for kw in ['list contact', 'show contact', 'all contact', 'my contact', 'contacts list'])

        if contacts_match or list_contacts or 'contact' in message_lower or 'who do i call' in message_lower or 'phone number' in message_lower or 'reach out' in message_lower:
            search_term = self._extract_contact_term(message_lower, contacts_match)
            return 'get_contacts', {'search_term': search_term}

        # Mentees
        if 'mentee' in message_lower or 'circle' in message_lower:
            store_filter = numbers[0] if numbers else None
            return 'get_mentees', {'store_nbr': store_filter}

        # Enablers
        if 'enabler' in message_lower or ('tip' in message_lower and 'trick' in message_lower):
            enabler_status = None
            if 'idea' in message_lower:
                enabler_status = 'idea'
            elif 'slide' in message_lower:
                enabler_status = 'slide_made'
            elif 'presented' in message_lower:
                enabler_status = 'presented'
            return 'get_enablers', {'status_filter': enabler_status}

        # Tasks
        if 'task' in message_lower or 'todo' in message_lower or 'to-do' in message_lower:
            task_status = status_filter
            if 'stalled' in message_lower:
                task_status = 'stalled'
            assigned = None
            assign_match = re.search(r'assigned to (\w+)', message_lower)
            if assign_match:
                assigned = assign_match.group(1)
            store_filter = numbers[0] if numbers else None
            return 'get_tasks', {'status_filter': task_status, 'assigned_to': assigned, 'store_number': store_filter}

        # User notes (not market notes)
        if 'note' in message_lower and ('my' in message_lower or 'user' in message_lower or 'personal' in message_lower or 'search note' in message_lower) and 'market' not in message_lower:
            search_match = re.search(r'(?:about|for|with)\s+["\']?([^"\']+)["\']?', message_lower)
            search_term = search_match.group(1).strip() if search_match else None
            return 'get_user_notes', {'search_query': search_term}

        # Champions
        if 'champion' in message_lower or ('team' in message_lower and 'contact' not in message_lower):
            return 'get_champions', {}

        # Gold stars
        if 'gold star' in message_lower or 'goldstar' in message_lower:
            week_num_match = re.search(r'(?:week|wk|w)\s*(\d{1,2})', message_lower)
            gold_star_week_num = int(week_num_match.group(1)) if week_num_match else None
            return 'get_gold_stars', {'week_number': gold_star_week_num}

        # Issues/feedback
        if 'issue' in message_lower or 'feedback' in message_lower or 'bug' in message_lower:
            type_filter = 'feedback' if 'feedback' in message_lower else ('issue' if 'issue' in message_lower or 'bug' in message_lower else None)
            return 'get_issues', {'status_filter': status_filter, 'type_filter': type_filter}

        # Market note status
        if 'market' in message_lower and ('status' in message_lower or 'progress' in message_lower or 'assigned' in message_lower or 'completion' in message_lower or 'outstanding' in message_lower or 'open' in message_lower or 'incomplete' in message_lower):
            return 'get_market_note_status', {'status_filter': status_filter}

        # Market note updates
        if 'market' in message_lower and 'update' in message_lower:
            return 'get_market_note_updates', {}

        # Summary/overview
        if 'summary' in message_lower or 'stats' in message_lower or 'overview' in message_lower:
            return 'get_summary_stats', {}

        # Market insights
        if 'market' in message_lower and ('insight' in message_lower or 'note' in message_lower):
            return 'get_market_insights', {}

        # Compare stores
        if 'compare' in message_lower and numbers:
            return 'compare_stores', {'store_list': ','.join(numbers)}

        # Trends/analysis
        if ('trend' in message_lower or 'analysis' in message_lower) and numbers:
            return 'analyze_trends', {'store_nbr': numbers[0]}

        # Search notes by keyword
        if 'search' in message_lower or 'find' in message_lower:
            match = re.search(r'(?:search|find)\s+(?:for\s+)?(?:stores?\s+with\s+)?["\']?([^"\']+)["\']?', message_lower)
            if match:
                keyword = match.group(1).strip()
                if keyword not in ['green', 'yellow', 'red', 'visits', 'visit', 'store', 'stores']:
                    return 'search_notes', {'keyword': keyword}
            if numbers:
                single_visit = bool(re.search(r'\b(last|most recent|latest)\s+visit\b', message_lower) and 'visits' not in message_lower)
                visit_limit = 1 if single_visit else 5
                return 'search_visits', {'store_nbr': numbers[0], 'limit': visit_limit, 'rating': rating_filter}

        # Store number present - search visits
        if numbers:
            single_visit = bool(re.search(r'\b(last|most recent|latest)\s+visit\b', message_lower) and 'visits' not in message_lower)
            visit_limit = 1 if single_visit else 5
            return 'search_visits', {'store_nbr': numbers[0], 'limit': visit_limit, 'rating': rating_filter}

        # Default fallback
        return 'get_summary_stats', {}

    def _extract_rating(self, message_lower: str) -> Optional[str]:
        """Extract rating filter from message"""
        if 'green' in message_lower:
            return 'Green'
        elif 'yellow' in message_lower:
            return 'Yellow'
        elif 'red' in message_lower:
            return 'Red'
        return None

    def _extract_status(self, message_lower: str) -> Optional[str]:
        """Extract status filter from message"""
        if 'in progress' in message_lower or 'in_progress' in message_lower:
            return 'in_progress'
        elif 'on hold' in message_lower or 'on_hold' in message_lower:
            return 'on_hold'
        elif 'completed' in message_lower or 'done' in message_lower:
            return 'completed'
        elif 'new' in message_lower or 'open' in message_lower:
            return 'new' if 'market' in message_lower else 'open'
        return None

    def _match_contacts(self, message_lower: str):
        """Check if message matches contact patterns"""
        for pattern in self.contacts_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match
        return None

    def _extract_contact_term(self, message_lower: str, contacts_match) -> Optional[str]:
        """Extract search term for contacts query"""
        search_term = None

        if contacts_match:
            search_term = contacts_match.group(1).strip().rstrip('?.,!')
        else:
            # Fallback extraction patterns
            fallback_patterns = [
                r'(?:about|for|with|regarding|on)\s+["\']?([^"\'?]+)["\']?',
                r'(?:named?|called)\s+["\']?([^"\'?]+)["\']?',
                r'(?:in|from|handles?|oversees?|over|runs?)\s+["\']?([^"\'?]+)["\']?',
            ]
            for pattern in fallback_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    search_term = match.group(1).strip()
                    break

        if search_term:
            # Clean up common noise words at the end
            noise_words = ['department', 'dept', 'area', 'section', 'team', 'the', 'a', 'an']
            words = search_term.split()
            while words and words[-1] in noise_words:
                words.pop()
            search_term = ' '.join(words) if words else search_term

            # Clean up common noise words at the start
            while words and words[0] in ['the', 'a', 'an', 'our', 'my']:
                words.pop(0)
            search_term = ' '.join(words) if words else search_term

        return search_term if search_term else None
