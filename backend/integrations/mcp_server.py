"""
Model Context Protocol (MCP) Server for Context Bank.
Implements the JSON-RPC 2.0 stdio transport protocol.
Exposes tools:
- list_contexts
- resolve_trigger
- retrieve_context
- search_contexts
- create_context
- update_context
"""
import sys
import json
import logging
from typing import Dict, Any, Optional

from backend.database.connection import SessionLocal
from backend.database.models import User, ContextTrigger, Context
from backend.core.security import hash_api_key
from backend.context_bank.retrieval import ContextRetrievalEngine
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.storage import ContextStorage
from backend.services.search_service import SearchService
from backend.schemas.contexts import ContextCreate, ContextUpdate
from backend.core.exceptions import TriggerNotFoundError, TriggerAlreadyExistsError, ContextNotFoundError

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger("mcp_server")

TOOLS = [
    {
        "name": "resolve_trigger",
        "description": "Resolve an exact trigger word (e.g. 'VOXCENT', 'SQLPATH') to find its associated context ID and summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trigger_word": {"type": "string", "description": "The exact registered trigger word"}
            },
            "required": ["trigger_word"]
        }
    },
    {
        "name": "retrieve_context",
        "description": "Retrieve an AI-ready context package containing decisions, next steps, and state for a registered trigger word.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trigger_word": {"type": "string", "description": "Registered trigger word, e.g. 'VOXCENT'"},
                "detail_level": {
                    "type": "string",
                    "enum": ["summary_only", "summary_and_state", "detailed", "full_archive"],
                    "default": "summary_and_state",
                    "description": "Amount of context detail to retrieve"
                }
            },
            "required": ["trigger_word"]
        }
    },
    {
        "name": "search_contexts",
        "description": "Search contexts by topic, meaning, or keywords when the exact trigger is unknown.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or question"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_contexts",
        "description": "List all contexts saved in the user's Context Bank namespace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Optional category filter"}
            }
        }
    },
    {
        "name": "create_context",
        "description": "Create a new context with a primary trigger word, summary, decisions, and next steps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trigger_word": {"type": "string", "description": "Uppercase trigger word"},
                "title": {"type": "string", "description": "Descriptive title"},
                "summary": {"type": "string", "description": "Concise summary"},
                "status": {"type": "string", "default": "Active"},
                "category": {"type": "string", "default": "Projects"},
                "confirmed_decisions": {"type": "array", "items": {"type": "string"}},
                "next_steps": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["trigger_word", "title", "summary"]
        }
    },
    {
        "name": "update_context",
        "description": "Update an existing context's summary, next steps, or status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "context_id": {"type": "string", "description": "Context ID"},
                "summary": {"type": "string"},
                "status": {"type": "string"},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "change_summary": {"type": "string", "default": "MCP client update"}
            },
            "required": ["context_id"]
        }
    }
]


class MCPServer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def _get_user(self, db) -> User:
        if self.api_key:
            kh = hash_api_key(self.api_key)
            u = db.query(User).filter(User.api_key_hash == kh).first()
            if u:
                return u
        # Fallback to first active user in local database
        u = db.query(User).filter(User.is_active == True).first()
        if not u:
            raise RuntimeError("No active user found in database.")
        return u

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            user = self._get_user(db)

            if name == "resolve_trigger":
                trig = TriggerRegistry.resolve_exact_trigger(db, user.id, args["trigger_word"])
                ctx = db.query(Context).filter(Context.id == trig.context_id).first()
                db.commit()
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Trigger '{trig.trigger_word}' resolved to Context ID '{trig.context_id}'. Title: '{ctx.title}'. Summary: {ctx.summary}"
                    }]
                }

            elif name == "retrieve_context":
                level = args.get("detail_level", "summary_and_state")
                pkg = ContextRetrievalEngine.retrieve_by_exact_trigger(
                    db=db,
                    user_id=user.id,
                    trigger_word=args["trigger_word"],
                    detail_level=level,
                    output_format="markdown",
                    accessed_via="mcp",
                )
                db.commit()
                return {
                    "content": [{
                        "type": "text",
                        "text": pkg.package_content
                    }]
                }

            elif name == "search_contexts":
                res = SearchService.search(
                    db=db,
                    user_id=user.id,
                    query=args["query"],
                    limit=args.get("limit", 5),
                )
                items_str = []
                for r in res.results:
                    items_str.append(f"- [{r.primary_trigger}] {r.title}: {r.summary} ({r.match_reason})")
                out = f"Found {res.total_results} matching contexts:\n" + "\n".join(items_str)
                return {"content": [{"type": "text", "text": out}]}

            elif name == "list_contexts":
                contexts, total = ContextStorage.list_contexts(
                    db=db,
                    user_id=user.id,
                    category=args.get("category"),
                )
                lines = [f"Total saved contexts: {total}"]
                for c in contexts:
                    trigs = TriggerRegistry.list_triggers_for_context(db, c.id)
                    primary = next((t.trigger_word for t in trigs if t.is_primary), "UNKNOWN")
                    lines.append(f"- `{primary}`: {c.title} (Status: {c.status})")
                return {"content": [{"type": "text", "text": "\n".join(lines)}]}

            elif name == "create_context":
                create_data = ContextCreate(
                    trigger_word=args["trigger_word"],
                    title=args["title"],
                    summary=args["summary"],
                    status=args.get("status", "Active"),
                    category=args.get("category", "Projects"),
                    important_decisions=[{"text": d} for d in args.get("confirmed_decisions", [])],
                    next_steps=args.get("next_steps", []),
                )
                ctx, trig = ContextStorage.create_context(db, user.id, create_data)
                db.commit()
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Successfully created context '{ctx.title}' under trigger '{trig.trigger_word}' (ID: {ctx.id})."
                    }]
                }

            elif name == "update_context":
                update_data = ContextUpdate(
                    summary=args.get("summary"),
                    status=args.get("status"),
                    next_steps=args.get("next_steps"),
                    change_summary=args.get("change_summary", "Updated via MCP"),
                )
                ctx = ContextStorage.update_context(db, args["context_id"], user.id, update_data)
                db.commit()
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Context '{ctx.title}' (ID: {ctx.id}) updated successfully."
                    }]
                }

            else:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}]
                }

        except Exception as e:
            db.rollback()
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error executing tool '{name}': {str(e)}"}]
            }
        finally:
            db.close()

    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "context-bank-mcp",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS}
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }

        elif msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
        return None

    def run_stdio(self):
        """Standard IO loop reading lines and sending responses."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                response = self.process_message(msg)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error handling message: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Context Bank MCP Server")
    parser.add_argument("--api-key", help="API key for authentication", default=None)
    parsed_args = parser.parse_args()

    server = MCPServer(api_key=parsed_args.api_key)
    server.run_stdio()
