"""
JaxAI Agent Orchestrator
Coordinates ADK agent with manual fallback routing.
"""

import json
import logging
from typing import Optional

from llm_provider import LLMProvider, create_provider
from manual_router import ManualRouter
from tools import ALL_TOOLS
from tools.db import set_db_pool

logger = logging.getLogger(__name__)

# System prompt for JaxAI
SYSTEM_PROMPT = """You are Jax, a helpful assistant for analyzing store visit data for a Walmart retail district manager.

You have access to tools that query a database containing:
- Store visits with ratings (Green, Yellow, Red) and metrics
- Market notes and their completion status
- Gold stars (weekly focus areas) and store completions
- Champions (team members) and their responsibilities
- Mentees in the mentee circle
- Contacts (people of interest)
- Enablers (tips/tricks)
- Issues and feedback
- Tasks with priorities and assignments
- Personal user notes

=== RESPONSE FORMAT ===
Choose the appropriate format based on the question type:

**FOR SIMPLE LOOKUPS** (who is X, what's the phone number, find contact, etc.):
- Give a direct, conversational answer
- Just provide the requested info naturally
- No special formatting needed

**FOR SUMMARIES/INSIGHTS** (summarize, analyze, what's the status, give me insights, overview, how are things going, etc.):
Use Smart Brevity format:

1. **THE BIG PICTURE** (1 sentence)
   Lead with the single most important takeaway. Be direct and specific.

2. **WHY IT MATTERS** (1-2 sentences)
   Explain the significance or impact. What should they care about?

3. **KEY DETAILS** (bullet points)
   - Use short, scannable bullets
   - One idea per bullet
   - Include specific numbers, dates, names, statuses
   - Max 5-7 bullets unless more detail is requested

4. **WHAT'S NEXT** (optional, if action needed)
   Specific next steps or recommendations.

=== STYLE RULES ===
- Be concise. No fluff or filler words.
- Use bold for emphasis on key points
- Numbers over words (use "5" not "five")
- Active voice, present tense
- If data is missing, acknowledge it briefly and move on
"""

# Mapping of tool names to functions for manual router
TOOL_FUNCTIONS = {tool.__name__: tool for tool in ALL_TOOLS}


class JaxAIOrchestrator:
    """Orchestrates JaxAI responses using ADK agent with fallback"""

    def __init__(self, llm_provider: LLMProvider = None, db_pool=None):
        self.llm_provider = llm_provider or create_provider()
        self.manual_router = ManualRouter()
        self.adk_agent = None

        # Set db pool for tools
        if db_pool:
            set_db_pool(db_pool)

        # Try to create ADK agent
        self._init_adk_agent()

    def _init_adk_agent(self):
        """Initialize ADK agent if available"""
        try:
            from google.adk.agents import Agent

            self.adk_agent = Agent(
                model=self.llm_provider.get_model_string(),
                name="jax_assistant",
                description="Store visit analytics assistant for retail district managers",
                instruction=SYSTEM_PROMPT,
                tools=ALL_TOOLS
            )
            logger.info("ADK agent initialized successfully")
        except ImportError:
            logger.warning("ADK not available, using fallback only")
            self.adk_agent = None
        except Exception as e:
            logger.error(f"Failed to initialize ADK agent: {e}")
            self.adk_agent = None

    def process_message(self, message: str) -> dict:
        """
        Process a chat message and return response.

        Args:
            message: User's question/message

        Returns:
            Dict with 'response' and 'source' keys
        """
        # Try ADK agent first if available
        if self.adk_agent and self.llm_provider.is_available():
            try:
                result = self._invoke_adk_agent(message)
                return {"response": result, "source": "adk_agent"}
            except Exception as e:
                logger.warning(f"ADK agent failed, falling back: {e}")

        # Fallback to manual routing + LLM formatting
        return self._fallback_response(message)

    def _invoke_adk_agent(self, message: str) -> str:
        """Invoke ADK agent to handle message"""
        # ADK agent handles tool selection and response generation
        response = self.adk_agent.run(message)
        return response.text if hasattr(response, 'text') else str(response)

    def _fallback_response(self, message: str) -> dict:
        """Manual routing fallback when ADK/LLM unavailable"""
        # Route to appropriate tool
        tool_name, kwargs = self.manual_router.route(message)
        logger.info(f"Manual router selected: {tool_name} with {kwargs}")

        # Execute tool
        tool_func = TOOL_FUNCTIONS.get(tool_name)
        if not tool_func:
            return {"response": "Sorry, I couldn't process that request.", "source": "error"}

        try:
            tool_result = tool_func(**kwargs)
            tool_data = json.loads(tool_result)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"response": f"Error retrieving data: {e}", "source": "error"}

        # Try LLM formatting if available
        if self.llm_provider.is_available():
            try:
                formatted = self._format_with_llm(message, tool_data)
                return {"response": formatted, "source": "gemini"}
            except Exception as e:
                logger.warning(f"LLM formatting failed: {e}")

        # Ultimate fallback: template formatting
        formatted = self._format_fallback(tool_name, tool_data)
        return {"response": formatted, "source": "formatted_fallback"}

    def _format_with_llm(self, message: str, data: dict) -> str:
        """Format tool results using LLM"""
        prompt = f"""{SYSTEM_PROMPT}

User's question: {message}

Data from database:
{json.dumps(data, indent=2)}

Please provide a helpful response based on this data."""

        return self.llm_provider.format_response(prompt)

    def _format_fallback(self, tool_name: str, data) -> str:
        """Template-based formatting when LLM unavailable"""
        if isinstance(data, dict) and 'error' in data:
            return f"Error: {data['error']}"

        if tool_name == 'get_summary_stats':
            return self._format_summary_stats(data)
        elif tool_name == 'get_champions':
            return self._format_champions(data)
        elif tool_name == 'get_contacts':
            return self._format_contacts(data)
        elif tool_name == 'get_mentees':
            return self._format_mentees(data)
        elif tool_name == 'get_gold_stars':
            return self._format_gold_stars(data)
        elif tool_name == 'get_tasks':
            return self._format_tasks(data)
        elif tool_name == 'search_visits':
            return self._format_visits(data)

        # Default: pretty JSON
        return f"Here's what I found:\n\n```json\n{json.dumps(data, indent=2)}\n```"

    def _format_summary_stats(self, data: dict) -> str:
        """Format summary stats"""
        return f"""**Store Visit Summary**

- Total visits: {data.get('total_visits', 0)}
- Unique stores: {data.get('unique_stores', 0)}
- Date range: {data.get('first_visit', 'N/A')} to {data.get('last_visit', 'N/A')}

**Ratings:**
- Green: {data.get('green_count', 0)}
- Yellow: {data.get('yellow_count', 0)}
- Red: {data.get('red_count', 0)}

Recent activity (30d): {data.get('recent_visits_30d', 0)} visits"""

    def _format_champions(self, data: list) -> str:
        """Format champions list"""
        if not data:
            return "No champions found."
        lines = ["**Champions:**"]
        for c in data:
            lines.append(f"- **{c.get('name', 'Unknown')}**: {c.get('responsibility', 'No responsibility assigned')}")
        return "\n".join(lines)

    def _format_contacts(self, data: list) -> str:
        """Format contacts list"""
        if not data:
            return "No contacts found."
        lines = ["**Contacts:**"]
        for c in data:
            name = c.get('name', 'Unknown')
            title = c.get('title', '')
            dept = c.get('department', '')
            phone = c.get('phone', '')
            email = c.get('email', '')
            info = f"- **{name}**"
            if title:
                info += f" - {title}"
            if dept:
                info += f" ({dept})"
            if phone:
                info += f"\n  Phone: {phone}"
            if email:
                info += f"\n  Email: {email}"
            lines.append(info)
        return "\n".join(lines)

    def _format_mentees(self, data: list) -> str:
        """Format mentees list"""
        if not data:
            return "No mentees found."
        lines = ["**Mentee Circle:**"]
        for m in data:
            lines.append(f"- **{m.get('name', 'Unknown')}** - Store {m.get('store_nbr', 'N/A')}, {m.get('position', 'N/A')}")
            if m.get('cell_number'):
                lines.append(f"  Cell: {m['cell_number']}")
        return "\n".join(lines)

    def _format_gold_stars(self, data: dict) -> str:
        """Format gold stars"""
        week_num = data.get('week_number', 'N/A')
        notes = data.get('notes', [])
        lines = [f"**Gold Stars - Week {week_num}**"]
        for i, note in enumerate(notes, 1):
            if note:
                lines.append(f"{i}. {note}")
        return "\n".join(lines)

    def _format_tasks(self, data: list) -> str:
        """Format tasks list"""
        if not data:
            return "No tasks found."
        lines = ["**Tasks:**"]
        for t in data:
            priority = t.get('priority', 0)
            priority_label = ['Low', 'Medium', 'High', 'Critical'][min(priority, 3)]
            status = t.get('status', 'unknown')
            content = t.get('content', 'No content')
            lines.append(f"- [{priority_label}] {content} ({status})")
            if t.get('assigned_to'):
                lines.append(f"  Assigned to: {t['assigned_to']}")
            if t.get('due_date'):
                lines.append(f"  Due: {t['due_date']}")
        return "\n".join(lines)

    def _format_visits(self, data: list) -> str:
        """Format visits list"""
        if not data:
            return "No visits found."
        lines = ["**Recent Visits:**"]
        for v in data:
            store = v.get('storeNbr', 'N/A')
            date = v.get('calendar_date', 'N/A')
            rating = v.get('rating', 'N/A')
            lines.append(f"- Store {store} on {date} - **{rating}**")
            if v.get('sales_comp_wtd'):
                lines.append(f"  Sales Comp WTD: {v['sales_comp_wtd']}")
            if v.get('top_3'):
                lines.append(f"  Improvements: {', '.join(v['top_3'][:3])}")
        return "\n".join(lines)


# Singleton instance for use in main.py
_orchestrator: Optional[JaxAIOrchestrator] = None


def get_orchestrator(db_pool=None) -> JaxAIOrchestrator:
    """Get or create the JaxAI orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = JaxAIOrchestrator(db_pool=db_pool)
    return _orchestrator


def process_chat_message(message: str, db_pool=None) -> dict:
    """Convenience function to process a chat message"""
    orchestrator = get_orchestrator(db_pool)
    return orchestrator.process_message(message)
