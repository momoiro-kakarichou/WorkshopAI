from typing import Dict, Any, Callable, List
import json
import datetime
import operator
import trafilatura
from googlesearch import search
from app.utils.utils import create_logger
from app.context import context

tool_service_log = create_logger(__name__, entity_name='TOOL_SERVICE', level=context.log_level)

# --- Standard Tool Implementations ---

def _get_current_datetime_impl() -> str:
    """Helper function: Returns the current date and time in ISO format."""
    tool_service_log.debug("Executing standard tool: get_current_datetime")
    return datetime.datetime.now().isoformat()

def _simple_calculator_impl(operand1: float, operator_str: str, operand2: float) -> float:
    """
    Helper function: Performs a simple arithmetic calculation.
    Supported operators: +, -, *, /
    """
    tool_service_log.debug(f"Executing standard tool: simple_calculator with {operand1} {operator_str} {operand2}")
    ops = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
    }
    if operator_str not in ops:
        tool_service_log.error(f"Unsupported operator in simple_calculator: {operator_str}")
        raise ValueError(f"Unsupported operator: {operator_str}. Use one of '+', '-', '*', '/'.")
    if operator_str == '/' and operand2 == 0:
        tool_service_log.error("Division by zero attempt in simple_calculator")
        raise ValueError("Division by zero is not allowed.")
    result = ops[operator_str](operand1, operand2)
    tool_service_log.debug(f"Simple calculator result: {result}")
    return result

def _web_search_impl(query: str, num_results: int = 5) -> str:
    """
    Helper function: Performs a web search using the googlesearch library
    and returns top results including title, link, and description.

    Args:
        query: The search query string.
        num_results: The maximum number of results to return.

    Returns:
        A formatted string containing the search results (title, link, description),
        or an error message if the search fails.
    """
    tool_service_log.debug(f"Executing standard tool: web_search with query: '{query}', num_results: {num_results}")

    try:
        search_results_generator = search(
            query,
            num_results=num_results,
            sleep_interval=2.0,
            advanced=True,
            unique=True
        )
        search_results = list(search_results_generator)


        if not search_results:
            tool_service_log.warning(f"No search results found for query: '{query}' using googlesearch (advanced).")
            return f"No search results found for query: '{query}'."

        results_list = []
        for result in search_results:
            title = result.title
            link = result.url
            snippet = result.description if result.description else "No snippet available."
            results_list.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n---")

        formatted_results = "\n".join(results_list).strip('\n---')
        tool_service_log.debug(f"Web search successful for query: '{query}'. Found {len(search_results)} results.")
        return formatted_results

    except Exception as e:
        tool_service_log.exception(f"Web search failed for query '{query}' using googlesearch (advanced). Error: {e}")
        return f"An error occurred during web search using googlesearch: {e}"
    
def _get_webpage_content_impl(url: str) -> str:
    """
    Helper function: Fetches a webpage and extracts its main text content using trafilatura.

    Args:
        url: The URL of the web page.

    Returns:
        The extracted text content as a string, or an error message if fetching/extraction fails.
    """
    tool_service_log.debug(f"Executing standard tool: get_webpage_content with url: '{url}'")
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        tool_service_log.error(f"Failed to fetch URL: {url}")
        return f"Error: Could not fetch content from URL: {url}"
    
    try:
        result = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        if result:
            tool_service_log.debug(f"Successfully extracted content from URL: {url}")
            return result
        else:
            tool_service_log.warning(f"Trafilatura extracted no main content from URL: {url}")
            return "No main content could be extracted from the page."
    except Exception as e:
        tool_service_log.exception(f"Error during trafilatura extraction for URL '{url}': {e}")
        return f"An error occurred during content extraction: {e}"

# --- Standard Tool Schemas ---

_GET_CURRENT_DATETIME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": "Gets the current server date and time in ISO format.",
        "parameters": {"type": "object", "properties": {}}
    }
}

_SIMPLE_CALCULATOR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "simple_calculator",
        "description": "Performs a simple arithmetic calculation (+, -, *, /) on two numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "operand1": {"type": "number", "description": "The first number."},
                "operator_str": {
                    "type": "string",
                    "description": "The arithmetic operator.",
                    "enum": ["+", "-", "*", "/"]
                 },
                "operand2": {"type": "number", "description": "The second number."}
            },
            "required": ["operand1", "operator_str", "operand2"]
        }
    }
}

_WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Performs a web search using Google and returns top results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "num_results": {
                    "type": "integer",
                    "description": "The maximum number of search results to return (default: 5).",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

_GET_WEBPAGE_CONTENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_webpage_content",
        "description": "Extracts the main textual content from a given web page URL using trafilatura.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL of the web page to extract content from."}
            },
            "required": ["url"]
        }
    }
}


class ToolService:
    """
    Manages the registration and execution of tools that can be called by AI models.
    Also maintains a list of standard tools that can be registered on demand.
    """
    _standard_tools: Dict[str, tuple[Callable, Dict[str, Any]]] = {
        "get_current_datetime": (_get_current_datetime_impl, _GET_CURRENT_DATETIME_SCHEMA),
        "simple_calculator": (_simple_calculator_impl, _SIMPLE_CALCULATOR_SCHEMA),
        "web_search": (_web_search_impl, _WEB_SEARCH_SCHEMA),
        "get_webpage_content": (_get_webpage_content_impl, _GET_WEBPAGE_CONTENT_SCHEMA),
    }

    def __init__(self):
        self._tools: Dict[str, Dict[str, Callable]] = {}
        self._tool_schemas: Dict[str, List[Dict[str, Any]]] = {}

    def register_tool(self, agent_id: str, name: str, func: Callable, schema: Dict[str, Any]):
        """Registers a new tool for a specific agent. Overwrites if already exists."""
        if not agent_id:
            tool_service_log.error("Agent ID is required to register a tool.")
            raise ValueError("Agent ID cannot be empty.")

        agent_tools = self._tools.setdefault(agent_id, {})
        agent_schemas = self._tool_schemas.setdefault(agent_id, [])

        agent_tools[name] = func
        
        agent_schemas[:] = [s for s in agent_schemas
                            if not (s.get("type") == "function" and
                                    s.get("function", {}).get("name") == name)]
        
        schema_copy = schema.copy()
        if schema_copy.get("type") == "function" and "function" in schema_copy:
            schema_copy["function"]["name"] = name
        agent_schemas.append(schema_copy)
        
        tool_service_log.info(f"Registered tool '{name}' for agent '{agent_id}'.")

    def delete_tool(self, agent_id: str, name: str):
        """Deletes a tool for a specific agent."""
        if not agent_id:
            tool_service_log.error("Agent ID is required to delete a tool.")
            raise ValueError("Agent ID cannot be empty.")

        if agent_id in self._tools and name in self._tools[agent_id]:
            del self._tools[agent_id][name]
            
            if agent_id in self._tool_schemas:
                self._tool_schemas[agent_id] = [s for s in self._tool_schemas[agent_id]
                                                if not (s.get("type") == "function" and
                                                        s.get("function", {}).get("name") == name)]
                if not self._tool_schemas[agent_id]:
                    del self._tool_schemas[agent_id]
            
            if not self._tools[agent_id]:
                del self._tools[agent_id]
                
            tool_service_log.info(f"Deleted tool '{name}' for agent '{agent_id}'.")
        else:
            tool_service_log.warning(f"Attempted to delete non-existent tool '{name}' for agent '{agent_id}'.")

    def register_standard_tool(self, agent_id: str, name: str):
        """Registers a standard tool by its name for a specific agent."""
        if not agent_id:
            tool_service_log.error("Agent ID is required to register a standard tool.")
            raise ValueError("Agent ID cannot be empty.")

        if name in self._standard_tools:
            func, schema = self._standard_tools[name]
            
            agent_tools = self._tools.setdefault(agent_id, {})
            agent_schemas = self._tool_schemas.setdefault(agent_id, [])

            agent_tools[name] = func
            
            agent_schemas[:] = [s for s in agent_schemas
                                if not (s.get("type") == "function" and
                                        s.get("function", {}).get("name") == name)]
            
            schema_copy = schema.copy()
            if schema_copy.get("type") == "function" and "function" in schema_copy:
                schema_copy["function"]["name"] = name
            agent_schemas.append(schema_copy)
            
            tool_service_log.info(f"Registered standard tool '{name}' for agent '{agent_id}'.")
        else:
            tool_service_log.warning(f"Attempted to register unknown standard tool: {name} for agent '{agent_id}'")
            raise ValueError(f"Standard tool '{name}' not found in predefined list.")

    def get_standard_tool_names(self) -> List[str]:
        """Returns the names of all available standard (but not necessarily registered) tools."""
        return list(self._standard_tools.keys())

    def get_tool_schemas(self, agent_id: str) -> List[Dict[str, Any]]:
        """Returns the JSON schemas for all currently registered tools for a specific agent."""
        if not agent_id:
            tool_service_log.warning("Agent ID was not provided to get_tool_schemas. Returning empty list.")
            return []
        return self._tool_schemas.get(agent_id, [])

    def execute_tool(self, agent_id: str, tool_name: str, tool_args_json: str) -> Any:
        """
        Executes a registered tool by name for a specific agent with JSON string arguments.

        Args:
            agent_id: The ID of the agent for whom the tool is registered.
            tool_name: The name of the tool to execute.
            tool_args_json: A JSON string containing the arguments for the tool.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the tool is not found for the agent, or if arguments are invalid JSON.
            Exception: If the tool execution fails.
        """
        if not agent_id:
            tool_service_log.error("Agent ID is required to execute a tool.")
            raise ValueError("Agent ID cannot be empty.")

        agent_specific_tools = self._tools.get(agent_id)
        if not agent_specific_tools or tool_name not in agent_specific_tools:
            tool_service_log.error(f"Attempted to execute unknown or unregistered tool '{tool_name}' for agent '{agent_id}'.")
            raise ValueError(f"Tool '{tool_name}' not found or not registered for agent '{agent_id}'.")

        try:
            tool_args = json.loads(tool_args_json)
        except json.JSONDecodeError as e:
            tool_service_log.error(f"Invalid JSON arguments for tool '{tool_name}' (agent '{agent_id}'): {e}")
            raise ValueError(f"Invalid JSON arguments for tool '{tool_name}': {e}") from e

        tool_func = agent_specific_tools[tool_name]
        tool_service_log.info(f"Executing tool '{tool_name}' for agent '{agent_id}' with args: {tool_args}")
        try:
            result = tool_func(**tool_args)
            tool_service_log.info(f"Tool '{tool_name}' for agent '{agent_id}' executed successfully.")
            try:
                json.dumps(result)
            except TypeError as json_err:
                tool_service_log.warning(f"Tool '{tool_name}' (agent '{agent_id}') result might not be JSON serializable: {json_err}")
            return result
        except Exception as e:
            tool_service_log.exception(f"Error executing tool '{tool_name}' for agent '{agent_id}': {e}")
            raise