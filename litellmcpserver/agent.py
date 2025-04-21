from typing import Any, Dict, List, Tuple
import subprocess
import json, os
import rich
import click
import litellm
from dotenv import load_dotenv
from pydantic import BaseModel
import rich.prompt

load_dotenv()

console = rich.console.Console()

class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPAgent:
    def __init__(self, config_path: str = "config.json", model: str= "gemini/gemini-2.0-flash"):
        self.model = model
        self.config = self._load_config(config_path=config_path)
        # console.print(f"[bold red]{self.config}[/bold red]")
        self.mcp_processes: Dict[str, Tuple[subprocess.Popen, Dict[str, str]]] = {}
        self.tools: List[Dict] = []
        self.lite_llm_tools: List[Dict] = []
        self.conversation_history: List[Dict[str, Any]] = []

    
    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, "r") as config:
                return json.load(config)
        except Exception as e:
            console.print(f"[red]Error loading config[/red]")
            return {"mcpServers": {}}

    def _discover_tools(self)->List[Dict]:
        all_tools = []
        
        for server_name, server_config in self.config.get("mcpServers", {}).items():
            try:
                # console.print(f"[green]{server_name} :: {server_config}[/green]")
                process, env = self._start_mcp_server(server_name=server_name)
                # console.print(f"{process}::{env}")
                server_tools = self._list_mcp_tools(process, server_name)
                # console.print(f"[bold yellow] {server_tools}[/bold yellow]")
                all_tools.extend(server_tools)
                # console.print(f"[green] discovered {len(server_tools)} tools in {server_name} [/green]")
            except Exception as e:
                console.print(f"[yellow] No tools discovered in {server_name} [/yellow]")
                continue
        return all_tools
            
    def chat(self):
        console.print("[bold blue]MCP Agent Chat[/bold blue]")
        console.print("Type 'exit' or 'quit' to end the session\n")
        self.tools = self._discover_tools()
        if not self.tools:
            console.print("[yellow]Warning: No MCP tools discovered[/yellow]")
            return
        self.lite_llm_tools = self._convert_mcp_tools_to_litellm(self.tools)
        console.print(f"[green]Total number of tools :: {len(self.tools)} [/green]")
        # chat loop
        while True:
            user_input: str = click.prompt("You")
            if user_input.lower() in ["exit", "quit"]:
                break
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            reponse = litellm.completion(
                model = self.model,
                messages = self.conversation_history,
                tools=self.tools,
                tool_choice="auto"
            )
            assistant_message = reponse.choices[0].message
            tool_calls = getattr(assistant_message, "tool_calls", None)

            if assistant_message.content:
                self.conversation_history.append({
                    "role": "user",
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
                        mcp_tool = self._convert_litellm_tool_call_to_mcp(tool_call)
                        if self._get_tool_permission

    def _get_tool_permission(self, tool_call: MCPToolCall) -> bool:
        """Ask for permission to execute an MCP tool call"""
        console.print("\n[yellow]MCP Tool Call Request:[/yellow]")
        console.print(f"Tool: [cyan]{tool_call.name}[/cyan]")
        console.print("Arguments:")
        for key, value in tool_call.arguments.items():
            console.print(f"  [green]{key}[/green]: {value}")
        
        return rich.prompt.Confirm.ask("\nAllow this tool call?")

    def _convert_litellm_tool_call_to_mcp(self, tool_call)->MCPToolCall:
        return MCPToolCall(
            name = tool_call.function.name,
            arguments = json.loads(tool_call.function.arguments)
        )

    def _convert_mcp_tools_to_litellm(self, mcp_tools: List[dict])->List[Dict]:
        litellm_tools = []
        # console.print(mcp_tools)
        for tool in mcp_tools:
            try:
                input_schema = tool.get("inputschema", {})
                if input_schema.get("type") == "object" and not input_schema.get("properties"):
                    input_schema["properties"] = {"dummy": {"name": "String", "description": "placeholder parameter"}}
                
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

        console.print("\n[dim]Debug - Converted to LiteLLM tools:[/dim]")
        for tool in litellm_tools:
            console.print(f"[dim]  - {tool['function']['name']}[/dim]")
            
        return litellm_tools


    def _start_mcp_server(self, server_name: str)->Tuple[subprocess.Popen, Dict[str, str]]:
        if server_name not in self.mcp_processes:
            server_config = self.config["mcpServers"].get(server_name)

        command = [server_config["command"]] + server_config["args"]
        # console.print(command)

        env = os.environ.copy()
        if "env" in server_config:
            env.update(server_config["env"])

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,       # Capture standard output
            stderr=subprocess.PIPE,       # Capture standard error
            stdin=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )
        self.mcp_processes[server_name] = (process, env)
        # console.print(f"[green] MCP Server started :: {server_name} [/green]")
        return self.mcp_processes[server_name]
    
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
        
def main():
    mcp = MCPAgent()
    mcp.chat()
    
if __name__ == "__main__":
    main()