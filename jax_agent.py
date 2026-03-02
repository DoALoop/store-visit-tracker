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

You have access to tools that can QUERY data AND TAKE ACTIONS.

=== ⚠️ RULE #1 — HIGHEST PRIORITY: ASSOCIATE INSIGHT DETECTION ===
BEFORE doing anything else, scan every incoming message for conversational cues about a person.

**TRIGGER PHRASES** — If the user says ANY of these, this is an Associate Insight request:
- "I talked to [name]"
- "I spoke with [name]"
- "I spent time with [name]"
- "I met with [name]"
- "I was with [name]"
- "I ran into [name]"
- "I visited [name]"
- "[name] told me / said / mentioned"
- "[name] said that..."
- "had a conversation with [name]"
- "caught up with [name]"

**MANDATORY WORKFLOW when a trigger phrase is detected:**
1. IMMEDIATELY recognize this as an Associate Insight log request. Do NOT pull store data. Do NOT summarize visits.
2. Use `get_contacts` to search for the person by name.
3. If FOUND: Extract the insight from the message and call `log_associate_insight(contact_id, insight)`. Confirm to the user: "Got it! I've logged that [name]'s [insight summary]."
4. If NOT FOUND: Ask the user: "I don't have [name] in your contacts yet. Could you give me their **full name, position, and store number** so I can add them before logging this?"
5. Once they provide details: call `create_contact(name, store_number, title)`, then call `log_associate_insight(new_contact_id, insight)`.

**NEVER respond with store visit data, summaries, or unrelated information when a trigger phrase is detected.**

=== QUERY CAPABILITIES ===
You can search and retrieve:
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
- Store information (manager, volume tier, format, location)
- Associate Insights (personal tidbits, facts, and conversational notes about team members)

=== ACTION CAPABILITIES ===
You can TAKE ACTIONS on behalf of the user:

**Gold Stars:**
- Mark gold stars complete: "mark gold star 1 complete for store 1234"
- Update gold star notes for the week

**Contacts & Associates:**
- Add contacts: "add John Smith as meat coach, phone 555-1234"
- Delete contacts: "remove John Smith from contacts"
- Log insights/tidbits: See RULE #1 above — always detect conversational phrases automatically

**Tasks:**
- Create tasks: "create task to follow up with store 5678"
- Complete tasks: "mark task 42 as done"
- Delete tasks: "delete task 15"

**Market Notes:**
- Update status: "mark the freezer market note as in progress"
- Assign notes: "assign the freezer note to Mike"
- Add comments: "add comment 'checked today' to the freezer note"
- Mark complete: "complete the market note about freezer"

**Champions & Mentees:**
- Add champions: "add Sarah as champion for OGP"
- Add mentees: "add Mike from store 1234 to my mentee circle"
- Remove champions/mentees

**Enablers:**
- Mark complete: "mark enabler 5 complete for store 1234"
- Create enablers: "add new enabler: use cart pusher for 2pm"

**Issues:**
- Log feedback: "log feedback about slow loading"
- Report bugs: "report bug: app crashes on save"

When taking actions, CONFIRM what you did with specific details.

=== RESPONSE FORMAT ===
Choose the appropriate format based on the question type:

**FOR SINGLE RESULT LOOKUPS** (who is John, one specific contact):
- Give a direct, conversational answer in 1-2 sentences
- Include key details naturally: name, title, department, phone/email if available
- Example: "John Smith handles Meat. He's a Market Fresh Lead and you can reach him at 555-1234."

**FOR MULTIPLE RESULTS** (who has meat, list contacts, show all X):
- Start with a brief intro line if helpful
- List EACH result on its own line with a bullet point
- Format each entry consistently:
  • **Name** - Title (Department)
    Phone: xxx | Email: xxx
- Keep each entry scannable - don't write paragraphs

**FOR SUMMARIES/INSIGHTS** (summarize, analyze, what's the status, overview):
Use Smart Brevity format:

1. **THE BIG PICTURE** (1 sentence)
   Lead with the single most important takeaway.

2. **WHY IT MATTERS** (1-2 sentences)
   Explain the significance or impact.

3. **KEY DETAILS** (bullet points)
   - Short, scannable bullets
   - One idea per bullet
   - Include specific numbers, dates, names
   - Max 5-7 bullets

4. **WHAT'S NEXT** (optional)
   Specific next steps if action needed.

=== STYLE RULES ===
- Be concise. No fluff or filler words.
- Use **bold** for names and emphasis
- Use bullet points (•) for lists - one item per line
- Numbers over words (use "5" not "five")
- Active voice, present tense
- If no results found, say so directly
- NEVER dump raw JSON - always format nicely
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

        # ---- Special handler: Associate Insight by Name ----
        if tool_name == 'log_associate_insight_by_name':
            return self._handle_insight_by_name(kwargs.get('name', ''), kwargs.get('insight', message))

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

    def _handle_insight_by_name(self, name: str, insight: str) -> dict:
        """Look up a contact by name and log the insight, or ask for their details."""
        from tools.team import get_contacts, log_associate_insight, create_contact
        import json as _json

        # Search for the contact by name
        try:
            results_raw = get_contacts(search_term=name)
            contacts = _json.loads(results_raw)
        except Exception as e:
            return {"response": f"I had trouble searching your contacts: {e}", "source": "error"}

        if contacts and not isinstance(contacts, dict):
            # Found matches — use the best one
            contact = contacts[0]
            contact_id = contact.get('id')
            contact_name = contact.get('name', name)
            try:
                log_associate_insight(contact_id=contact_id, insight=insight)
                return {
                    "response": (
                        f"✓ Got it! I've logged that **{contact_name}** said:\n\n"
                        f"> {insight}\n\n"
                        f"This will now appear in their profile under Recent Insights on the Contacts page."
                    ),
                    "source": "insight_logged"
                }
            except Exception as e:
                return {"response": f"I found {contact_name} in your contacts but couldn't log the insight: {e}", "source": "error"}
        else:
            # Contact not found — ask for their details
            return {
                "response": (
                    f"I don't have **{name.title()}** in your contacts yet. Before I can save this insight, "
                    f"I need a little more info:\n\n"
                    f"1. **Full name** (first and last)\n"
                    f"2. **Position / title** (e.g., Store Manager, Market Lead)\n"
                    f"3. **Store number**\n\n"
                    f"Once you give me those, I'll add them to your contacts and log this right away! 🐾"
                ),
                "source": "insight_needs_contact"
            }


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

        # Check if this is an action result (has 'success' key)
        if isinstance(data, dict) and 'success' in data:
            return self._format_action_result(data)

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
        elif tool_name == 'get_store_information':
            return self._format_store_info(data)
        elif tool_name == 'get_associate_insights':
            return self._format_associate_insights(data)

        # Default: pretty JSON
        return f"Here's what I found:\n\n```json\n{json.dumps(data, indent=2)}\n```"

    def _format_action_result(self, data: dict) -> str:
        """Format action results (create, update, delete operations)"""
        if data.get('success'):
            message = data.get('message', 'Action completed successfully')
            response = f"✓ **Done!** {message}"

            # Add details if available
            if 'contact' in data:
                c = data['contact']
                response += f"\n\n**Contact added:**"
                response += f"\n• Name: {c.get('name', 'N/A')}"
                if c.get('title'):
                    response += f"\n• Title: {c['title']}"
                if c.get('department'):
                    response += f"\n• Department: {c['department']}"
                if c.get('phone'):
                    response += f"\n• Phone: {c['phone']}"
                if c.get('email'):
                    response += f"\n• Email: {c['email']}"

            elif 'task' in data:
                t = data['task']
                response += f"\n\n**Task details:**"
                response += f"\n• ID: #{t.get('id', 'N/A')}"
                response += f"\n• Content: {t.get('content', 'N/A')}"
                response += f"\n• Status: {t.get('status', 'new')}"
                if t.get('assigned_to'):
                    response += f"\n• Assigned to: {t['assigned_to']}"
                if t.get('store_number'):
                    response += f"\n• Store: {t['store_number']}"

            elif 'champion' in data:
                c = data['champion']
                response += f"\n\n• **{c.get('name', 'N/A')}** - {c.get('responsibility', 'N/A')}"

            elif 'mentee' in data:
                m = data['mentee']
                response += f"\n\n• **{m.get('name', 'N/A')}**"
                if m.get('store_nbr'):
                    response += f" - Store {m['store_nbr']}"
                if m.get('position'):
                    response += f", {m['position']}"

            elif 'enabler' in data:
                e = data['enabler']
                response += f"\n\n• **{e.get('title', 'N/A')}** ({e.get('status', 'idea')})"

            elif 'issue' in data:
                i = data['issue']
                response += f"\n\n• **{i.get('title', 'N/A')}** (#{i.get('id', 'N/A')}) - {i.get('type', 'issue')}"

            return response
        else:
            error = data.get('error', 'Unknown error')
            return f"✗ **Action failed:** {error}"

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

        if len(data) == 1:
            c = data[0]
            return f"**{c.get('name', 'Unknown')}** is the champion for {c.get('responsibility', 'their area')}."

        lines = [f"**{len(data)} Champions:**\n"]
        for c in data:
            lines.append(f"• **{c.get('name', 'Unknown')}** - {c.get('responsibility', 'No responsibility assigned')}")
        return "\n".join(lines)

    def _format_contacts(self, data: list) -> str:
        """Format contacts list"""
        if not data:
            return "No contacts found matching that search."

        # Single result - conversational
        if len(data) == 1:
            c = data[0]
            name = c.get('name', 'Unknown')
            title = c.get('title', '')
            dept = c.get('department', '')
            phone = c.get('phone', '')
            email = c.get('email', '')
            reports_to = c.get('reports_to', '')

            response = f"**{name}**"
            if title:
                response += f" is a {title}"
            if dept:
                response += f" over {dept}"
            response += "."

            contact_info = []
            if phone:
                contact_info.append(f"Phone: {phone}")
            if email:
                contact_info.append(f"Email: {email}")
            if reports_to:
                contact_info.append(f"Reports to: {reports_to}")

            if contact_info:
                response += "\n" + " | ".join(contact_info)

            return response

        # Multiple results - bulleted list
        lines = [f"Found {len(data)} contacts:\n"]
        for c in data:
            name = c.get('name', 'Unknown')
            title = c.get('title', '')
            dept = c.get('department', '')
            phone = c.get('phone', '')
            email = c.get('email', '')

            # Build main line
            line = f"• **{name}**"
            if title:
                line += f" - {title}"
            if dept:
                line += f" ({dept})"

            # Add contact details on same line if short, otherwise below
            contact_parts = []
            if phone:
                contact_parts.append(phone)
            if email:
                contact_parts.append(email)

            if contact_parts:
                line += f"\n  {' | '.join(contact_parts)}"

            lines.append(line)

        return "\n".join(lines)

    def _format_mentees(self, data: list) -> str:
        """Format mentees list"""
        if not data:
            return "No mentees found."

        if len(data) == 1:
            m = data[0]
            response = f"**{m.get('name', 'Unknown')}** at Store {m.get('store_nbr', 'N/A')} ({m.get('position', 'N/A')})"
            if m.get('cell_number'):
                response += f"\nCell: {m['cell_number']}"
            return response

        lines = [f"**Mentee Circle ({len(data)}):**\n"]
        for m in data:
            line = f"• **{m.get('name', 'Unknown')}** - Store {m.get('store_nbr', 'N/A')}, {m.get('position', 'N/A')}"
            if m.get('cell_number'):
                line += f"\n  Cell: {m['cell_number']}"
            lines.append(line)
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

        priority_labels = ['Low', 'Medium', 'High', 'Critical']

        if len(data) == 1:
            t = data[0]
            priority = priority_labels[min(t.get('priority', 0), 3)]
            status = t.get('status', 'unknown')
            content = t.get('content', 'No content')
            response = f"**[{priority}]** {content} - Status: {status}"
            if t.get('assigned_to'):
                response += f"\nAssigned to: {t['assigned_to']}"
            if t.get('due_date'):
                response += f" | Due: {t['due_date']}"
            return response

        lines = [f"**{len(data)} Tasks:**\n"]
        for t in data:
            priority = priority_labels[min(t.get('priority', 0), 3)]
            status = t.get('status', 'unknown')
            content = t.get('content', 'No content')
            line = f"• **[{priority}]** {content} ({status})"
            details = []
            if t.get('assigned_to'):
                details.append(f"Assigned: {t['assigned_to']}")
            if t.get('due_date'):
                details.append(f"Due: {t['due_date']}")
            if details:
                line += f"\n  {' | '.join(details)}"
            lines.append(line)
        return "\n".join(lines)

    def _format_visits(self, data: list) -> str:
        """Format visits list"""
        if not data:
            return "No visits found."

        if len(data) == 1:
            v = data[0]
            store = v.get('storeNbr', 'N/A')
            date = v.get('calendar_date', 'N/A')
            rating = v.get('rating', 'N/A')
            response = f"**Store {store}** on {date} - **{rating}**"
            if v.get('sales_comp_wtd'):
                response += f"\nSales Comp WTD: {v['sales_comp_wtd']}"
            if v.get('top_3') and len(v['top_3']) > 0:
                response += f"\nTop improvements: {', '.join(v['top_3'][:3])}"
            return response

        lines = [f"**{len(data)} Recent Visits:**\n"]
        for v in data:
            store = v.get('storeNbr', 'N/A')
            date = v.get('calendar_date', 'N/A')
            rating = v.get('rating', 'N/A')
            line = f"• **Store {store}** ({date}) - **{rating}**"
            if v.get('sales_comp_wtd'):
                line += f" | Comp: {v['sales_comp_wtd']}"
            lines.append(line)
        return "\n".join(lines)

    def _format_store_info(self, data: list) -> str:
        """Format store information list"""
        if not data:
            return "No store information found."
            
        if len(data) == 1:
            s = data[0]
            store = s.get('store_number', 'N/A')
            city = s.get('city', 'N/A')
            state = s.get('state', 'N/A')
            manager = s.get('store_manager', 'N/A')
            
            response = f"**Store {store}** ({city}, {state})"
            if manager and manager != 'N/A':
                response += f"\nManager: {manager}"
            if s.get('volume_tier'):
                response += f"\nVolume Tier: {s['volume_tier']}"
            if s.get('complex_tier'):
                response += f"\nComplex Tier: {s['complex_tier']}"
            return response
            
        lines = [f"**{len(data)} Stores Found:**\n"]
        for s in data:
            store = s.get('store_number', 'N/A')
            manager = s.get('store_manager', 'No manager listed')
            tier = s.get('volume_tier', '')
            
            line = f"• **Store {store}** - Manager: {manager}"
            if tier:
                line += f" | Vol: {tier}"
            lines.append(line)
        return "\n".join(lines)

    def _format_associate_insights(self, data: list) -> str:
        """Format associate insights list"""
        if not data:
            return "I don't have any insights logged for that associate."
            
        name = data[0].get('associate_name', 'Associate')
        lines = [f"**Insights for {name}:**\n"]
        for ins in data:
            text = ins.get('insight_text', '')
            date = ins.get('created_at', 'Unknown date')
            # Extract just the date part if it's an ISO string
            if 'T' in date:
                date = date.split('T')[0]
            
            line = f"• {text} *(Logged on {date})*"
            if ins.get('store_number'):
                line += f" [Store {ins['store_number']}]"
            lines.append(line)
            
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
