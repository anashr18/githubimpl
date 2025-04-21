#!/usr/bin/env python3
import os
import json
import base64
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import click
from rich.console import Console
from rich.prompt import Confirm
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel

# import litellm
# # litellm._turn_on_debug()
# Set up litellm debug mode to see what's happening
# litellm.set_verbose = True

console = Console()

# Load environment variables
load_dotenv()

# Configure LiteLLM with Google AI Studio credentials
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY environment variable is not set")

class MCPToolCall(BaseModel):
    """Represents a tool call in the MCP format"""
    name: str
    arguments: Dict[str, Any]

class MCPAgent:
    """Main agent class that handles:
    1. Converting between LiteLLM and MCP formats
    2. Managing MCP server processes
    3. Handling tool calls and responses
    4. Managing conversation state
    """
    def __init__(self, config_path: str = "config.json", model: str = "gemini/gemini-2.0-flash"):
        """Initialize the MCP agent
        
        Args:
            config_path: Path to the MCP config file
            model: Model to use. For Google AI Studio, must include the gemini/ prefix
                  e.g. gemini/gemini-2.0-flash
        """
        self.model = model
        self.config = self._load_config(config_path)
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Set up image directory - use absolute path for clarity
        workspace_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.image_dir = workspace_dir / "data" / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[blue]Images will be saved to: {self.image_dir}[/blue]")
        
        # Dict of active MCP server processes and their environments
        self.mcp_processes: Dict[str, Tuple[subprocess.Popen, Dict[str, str]]] = {}
        
        # Cache of discovered tools and their LiteLLM format
        self.tools: List[dict] = []
        self.litellm_tools: List[dict] = []

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {"mcpServers": {}}

    def _start_mcp_server(self, server_name: str) -> Tuple[subprocess.Popen, Dict[str, str]]:
        """Start an MCP server process if not already running"""
        if server_name not in self.mcp_processes:
            server_config = self.config["mcpServers"].get(server_name)
            if not server_config:
                raise ValueError(f"Unknown MCP server: {server_name}")

            # Get environment from config
            env = os.environ.copy()  # Start with current environment
            if "env" in server_config:
                env.update(server_config["env"])
            
            # Start the server process
            process = subprocess.Popen(
                [server_config["command"]] + server_config["args"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1
            )
            
            self.mcp_processes[server_name] = (process, env)
            console.print(f"[green]Started MCP server: {server_name}[/green]")
            
        return self.mcp_processes[server_name]

    def _save_image(self, image_data: str) -> str:
        """Save base64 image data and return the file path"""
        try:
            # Extract actual base64 data if it includes data URI scheme
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.image_dir / f"screenshot_{timestamp}.png"
            
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            
            return str(image_path)
        except Exception as e:
            console.print(f"[red]Error saving image: {e}[/red]")
            return ""

    def _list_mcp_tools(self, process, server_name: str) -> List[dict]:
        """Get tool definitions from an MCP server using the tools/list method"""
        try:
            # Send tools/list request
            list_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            process.stdin.write(json.dumps(list_request) + "\n")
            process.stdin.flush()
            
            # Read response
            response = process.stdout.readline()
            if not response:
                return []
                
            result = json.loads(response)
            if "error" in result:
                console.print(f"[red]Error listing tools: {result['error']}[/red]")
                return []
                
            tools = result.get("result", {}).get("tools", [])
            
            # Add server name to each tool for tracking
            for tool in tools:
                tool["server"] = server_name
                
            return tools
        except Exception as e:
            console.print(f"[red]Error listing tools: {e}[/red]")
            return []

    def _convert_mcp_tools_to_litellm(self, mcp_tools: List[dict]) -> List[dict]:
        """Convert MCP server tools to LiteLLM/OpenAI format
        
        Args:
            mcp_tools: List of MCP tool definitions
            
        Returns:
            List of tools in LiteLLM format
        """
        litellm_tools = []
        
        # Debug print incoming tools
        console.print("\n[dim]Debug - Converting the following MCP tools to LiteLLM format:[/dim]")
        for tool in mcp_tools:
            console.print(f"[dim]  - {tool.get('name', 'unknown')} from server {tool.get('server', 'unknown')}[/dim]")
        
        # Convert each tool definition to LiteLLM format
        for tool in mcp_tools:
            try:
                # Get the input schema
                input_schema = tool.get("inputSchema", {})
                
                # Ensure properties exist and are non-empty for object types
                if input_schema.get("type") == "object" and not input_schema.get("properties"):
                    input_schema["properties"] = {"dummy": {"type": "string", "description": "Placeholder parameter"}}
                
                # Recursively process nested object properties
                def process_schema(schema):
                    if not isinstance(schema, dict):
                        return schema
                    
                    # Handle object types
                    if schema.get("type") == "object":
                        if not schema.get("properties"):
                            schema["properties"] = {"dummy": {"type": "string", "description": "Placeholder parameter"}}
                        else:
                            # Process each property
                            for prop in schema["properties"].values():
                                process_schema(prop)
                    
                    # Handle string types with format
                    elif schema.get("type") == "string" and "format" in schema:
                        # Only allow 'date-time' and 'enum' formats for Vertex AI
                        if schema["format"] not in ["date-time", "enum"]:
                            del schema["format"]
                    
                    return schema
                
                # Process the entire schema
                processed_schema = process_schema(input_schema)
                
                litellm_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": processed_schema
                    }
                }
                litellm_tools.append(litellm_tool)
                
            except Exception as e:
                console.print(f"[yellow]Warning: Could not convert tool {tool.get('name', 'unknown')}: {e}[/yellow]")
                continue
        
        # Debug print converted tools
        console.print("\n[dim]Debug - Converted to LiteLLM tools:[/dim]")
        for tool in litellm_tools:
            console.print(f"[dim]  - {tool['function']['name']}[/dim]")
            
        return litellm_tools

    def _convert_litellm_tool_call_to_mcp(self, tool_call) -> MCPToolCall:
        """Convert LiteLLM/OpenAI tool call to MCP format"""
        # Create MCP tool call request
        return MCPToolCall(
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments)
        )

    def _convert_mcp_result_to_litellm(self, tool_call_id: str, mcp_result: dict) -> dict:
        """Convert MCP tool result to LiteLLM/OpenAI format
        
        After a tool executes, we need to convert its response from MCP format
        back to LiteLLM format so the LLM can process it.
        
        MCP returns: { content: [{ type: "text", text: string }], isError?: boolean }
        LiteLLM expects: { role: "tool", tool_call_id: string, content: string }
        """
        # MCP returns: { content: [{ type: "text", text: string }], isError?: boolean }
        if isinstance(mcp_result, dict):
            content = mcp_result.get("content", [])
            is_error = mcp_result.get("isError", False)
            
            # Combine all text content
            text_content = " ".join(
                item.get("text", "") 
                for item in content 
                if item.get("type") == "text"
            )
            
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": text_content
            }
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(mcp_result)
        }

    def _handle_tool_response(self, response: Dict[str, Any], tool_call_id: str) -> Dict[str, Any]:
        """Process tool response, handling images and returning context for LLM
        
        Returns:
            Dict containing the tool response in LiteLLM format
        """
        if not response:
            return {"role": "tool", "tool_call_id": tool_call_id, "content": "No response from tool"}

        console.print(f"\n[dim]Debug - Raw tool response: {json.dumps(response, indent=2)}[/dim]")

        # Handle screenshot or other image responses
        if isinstance(response, dict) and 'content' in response:
            content = response['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        # Handle image data
                        if item.get('type') == 'image' and 'data' in item:
                            image_data = item['data']
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            mime_type = item.get('mimeType', 'image/png')
                            image_path = self.image_dir / f"screenshot_{timestamp}.{mime_type.split('/')[-1]}"
                            
                            try:
                                # Save the image
                                with open(image_path, 'wb') as f:
                                    # Handle base64 encoded data
                                    if isinstance(image_data, str):
                                        # Remove any data URI prefix if present
                                        if ';base64,' in image_data:
                                            image_data = image_data.split(';base64,')[1]
                                        # Remove any newlines or spaces that might have been added
                                        image_data = image_data.replace('\n', '').replace(' ', '')
                                        f.write(base64.b64decode(image_data))
                                    else:
                                        # Handle binary data
                                        f.write(image_data)
                                
                                console.print(f"\n[green]Screenshot saved successfully to: {image_path}[/green]")
                                
                                # Read the image back as base64 for the LLM
                                with open(image_path, 'rb') as f:
                                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                                
                                # Store image data for later use after tool response is processed
                                self._pending_screenshot = {
                                    "mime_type": mime_type,
                                    "base64": image_base64,
                                    "path": str(image_path)
                                }
                                
                                # Return simple text-only tool response
                                return {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": "Screenshot captured successfully."
                                }
                                
                            except Exception as e:
                                console.print(f"[red]Error saving screenshot: {str(e)}[/red]")
                                return {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": f"Error saving screenshot: {str(e)}"
                                }

        # Handle normal text responses
        if isinstance(response, dict) and 'content' in response:
            content = response['content']
            if isinstance(content, list):
                text_content = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_content.append(item.get('text', ''))
                if text_content:
                    return {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": " ".join(text_content)
                    }

        # Return raw response if no special handling needed
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(response)
        }

    def _get_tool_permission(self, tool_call: MCPToolCall) -> bool:
        """Ask for permission to execute an MCP tool call"""
        console.print("\n[yellow]MCP Tool Call Request:[/yellow]")
        console.print(f"Tool: [cyan]{tool_call.name}[/cyan]")
        console.print("Arguments:")
        for key, value in tool_call.arguments.items():
            console.print(f"  [green]{key}[/green]: {value}")
        
        return Confirm.ask("\nAllow this tool call?")

    def _execute_tool(self, tool: MCPToolCall) -> Dict[str, Any]:
        """Execute an MCP tool call using the tools/call method"""
        try:
            # Debug print to show which tool we're trying to execute
            console.print(f"\n[dim]Debug - Attempting to execute tool: {tool.name}[/dim]")
            
            # Find the original tool definition to get its server
            original_tool = next((t for t in self.tools if t["name"] == tool.name), None)
            if not original_tool:
                raise ValueError(f"Tool {tool.name} not found in discovered tools")
            
            server_name = original_tool.get("server")
            if not server_name:
                raise ValueError(f"No server found for tool {tool.name}")
                
            console.print(f"[dim]Debug - Tool {tool.name} belongs to server: {server_name}[/dim]")
            
            # Start the correct server
            process, env = self._start_mcp_server(server_name)
            
            # Send tool call request
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool.name,
                    "arguments": tool.arguments
                }
            }
            
            # Debug print the request
            console.print(f"\n[dim]Debug - Tool call request: {json.dumps(call_request, indent=2)}[/dim]")
            
            process.stdin.write(json.dumps(call_request) + "\n")
            process.stdin.flush()
            
            # Read response
            response = process.stdout.readline()
            if not response:
                raise ValueError(f"No response from server {server_name}")
                
            result = json.loads(response)
            
            # Debug print the raw response
            console.print(f"\n[dim]Debug - Raw tool response: {json.dumps(result, indent=2)}[/dim]")
            
            if "error" in result:
                return {
                    "content": [{"type": "text", "text": f"Error: {result['error']}"}],
                    "isError": True
                }
                
            return result.get("result", {})
                
        except Exception as e:
            console.print(f"\n[red]Error executing tool {tool.name}: {str(e)}[/red]")
            return {
                "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                "isError": True
            }

    def __del__(self):
        """Cleanup MCP server processes on exit"""
        for process, _ in self.mcp_processes.values():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

    def _discover_tools(self) -> List[dict]:
        """Discover all available tools from MCP servers in config"""
        all_tools = []
        
        # Start each MCP server and list its tools
        for server_name, server_config in self.config.get("mcpServers", {}).items():
            try:
                process, env = self._start_mcp_server(server_name)
                server_tools = self._list_mcp_tools(process, server_name)
                all_tools.extend(server_tools)
                console.print(f"[green]Discovered {len(server_tools)} tools from {server_name}[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not discover tools from {server_name}: {e}[/yellow]")
                continue
        
        return all_tools

    def chat(self):
        """Interactive chat session with the agent"""
        console.print("[bold blue]MCP Agent Chat[/bold blue]")
        console.print("Type 'exit' or 'quit' to end the session\n")

        # Discover available tools first
        self.tools = self._discover_tools()
        if not self.tools:
            console.print("[yellow]Warning: No MCP tools discovered[/yellow]")
            return

        # Convert tools to LiteLLM format once
        self.litellm_tools = self._convert_mcp_tools_to_litellm(self.tools)
        console.print(f"\n[green]Total tools available: {len(self.litellm_tools)}[/green]")

        while True:
            user_input = click.prompt("You")
            
            if user_input.lower() in ['exit', 'quit']:
                break

            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            try:
                # Use the cached LiteLLM tools
                response = completion(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=self.litellm_tools,
                    tool_choice="auto"
                )

                assistant_message = response.choices[0].message
                tool_calls = getattr(assistant_message, 'tool_calls', None)

                # Add assistant's message to history before tool calls
                if assistant_message.content:
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message.content
                    })
                    console.print(f"\n[bold green]Assistant:[/bold green] {assistant_message.content}\n")

                if tool_calls:
                    for tool_call in tool_calls:
                        # Add the tool call to history first
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        })

                        # Convert to MCP format
                        mcp_tool = self._convert_litellm_tool_call_to_mcp(tool_call)

                        if self._get_tool_permission(mcp_tool):
                            try:
                                # Execute MCP tool call
                                mcp_result = self._execute_tool(mcp_tool)
                                
                                # Process result (including any images)
                                tool_result = self._handle_tool_response(mcp_result, tool_call.id)
                                if tool_result:
                                    # Add tool response to history
                                    self.conversation_history.append(tool_result)

                                    # If we have a pending screenshot, add it before getting follow-up response
                                    if hasattr(self, '_pending_screenshot') and self._pending_screenshot:
                                        self.conversation_history.append({
                                            "role": "assistant",
                                            "content": "I've captured the screenshot. Can you show it to me?"
                                        })
                                        
                                        self.conversation_history.append({
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Here is the screenshot that was captured:"
                                                },
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": f"data:{self._pending_screenshot['mime_type']};base64,{self._pending_screenshot['base64']}"
                                                    }
                                                }
                                            ]
                                        })
                                        
                                        # Clear the pending screenshot
                                        self._pending_screenshot = None

                                    # Always get a follow-up response from the assistant
                                    follow_up_response = completion(
                                        model=self.model,
                                        messages=self.conversation_history,
                                        tools=self.litellm_tools,
                                        tool_choice="auto"
                                    )
                                    
                                    follow_up_message = follow_up_response.choices[0].message
                                    if follow_up_message.content:
                                        self.conversation_history.append({
                                            "role": "assistant",
                                            "content": follow_up_message.content
                                        })
                                        console.print(f"\n[bold green]Assistant:[/bold green] {follow_up_message.content}\n")
                                    
                                    # If there are more tool calls, process them
                                    if getattr(follow_up_message, 'tool_calls', None):
                                        tool_calls.extend(follow_up_message.tool_calls)

                            except Exception as e:
                                # Handle tool execution error
                                error_result = {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error: {str(e)}"
                                }
                                self.conversation_history.append(error_result)
                                console.print(f"\n[red]Tool execution error: {str(e)}[/red]\n")
                        else:
                            # Handle rejected tool call with a proper tool response
                            tool_response = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": "Tool call was rejected by the user."
                            }
                            self.conversation_history.append(tool_response)
                            console.print("\n[yellow]Tool call was rejected by the user.[/yellow]\n")
                            continue

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

@click.command()
@click.option('--config', default='config.json', help='Path to MCP config file')
@click.option('--model', default='gemini/gemini-2.0-flash', help='LLM model to use')
def main(config: str, model: str):
    """MCP Agent - Interactive chat with MCP-enabled LLM"""
    load_dotenv()
    agent = MCPAgent(config_path=config, model=model)
    agent.chat()

if __name__ == '__main__':
    main() 