'''
ToolWrapper.call() + ToolWrapper.catalog()

Single point of execution for all registered tools:
  - call(name, args): lookup → validate (Pydantic) → execute → return result as str
  - catalog(): expose all tools as JSON Schema for the LLM 
'''

from .registry import TOOL_REGISTRY


class ToolWrapper:
    '''
    Static facade over TOOL_REGISTRY. Hides the registry internals from the
    rest of the codebase (agent.py, react_loop, etc.). Two responsibilities:
      1. Execute a tool by name with validated arguments.
      2. Produce a catalog of tool definitions in the format expected by the given LLM provider.
    '''

    @staticmethod
    def call(name:str, args:dict) -> str:
        '''
        Look up a tool by name, validate its arguments with Pydantic,
        execut it and return the result as a string.

        All errors are return as human-readable strings (Not raised),
        since LLM consume this output as an observation - stack traces would confuse it.
        '''

        # 1. Lookup
        if name not in TOOL_REGISTRY:
            return f"Error: tool '{name}' not found."
        
        tool = TOOL_REGISTRY[name]

         # 2. Validate with Pydantic (raises if args don't match the schema)
        try:
            params = tool["params_model"](**args)
        except Exception as e:
            return f"Error: invalid arguments for '{name}': {e}"
        
        # 3. Execute (catch any runtime error and surface it as text)
        try:
            return str(tool["func"](params))
        except Exception as e:
            return f"Error while executing '{name}': {e}"
    

    @staticmethod
    def catalog(provider: str = "anthropic") -> list[dict]:
        '''
        Return the registered tools as a list of tool definitions
        in the format expected by the given LLM provider.
        Supported providers: "anthropic", "openai".
        '''
        if provider == "anthropic":
            return [
                {
                    "name": name,
                    "description": tool["description"],
                    "input_schema": tool["params_model"].model_json_schema(),
                }
                for name, tool in TOOL_REGISTRY.items()
            ]

        if provider == "openai":
            return [
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool["description"],
                        "parameters": tool["params_model"].model_json_schema(),
                    },
                }
                for name, tool in TOOL_REGISTRY.items()
            ]

        raise ValueError(f"Unknown provider: '{provider}'. Use 'anthropic' or 'openai'.")