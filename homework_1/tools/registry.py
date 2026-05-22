'''
TOOL_REGISTRY + @register_tool decorator

Auto-registers tools by name. Validates that each tool has:
  - exactly one parameter of type BaseModel (Pydantic)
  - a non-empty docstring (becomes the description shown to the LLM)
'''

import inspect
from pydantic import BaseModel

# Global registry: name -> {"func": callable, "params_model": BaseModel class, "description": str}
TOOL_REGISTRY: dict[str, dict] = {}

def register_tool(func):
    '''
    Decorator that registers a function as a tool in TOOL_REGISTRY.
    
    Requirements:
     1. The function must take exactly one parameter of type BaseModel.
     2. The function must have a docstring (description visible by LLM)
    '''
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Validation 1: exactly one parameter, and it must be BaseModel subclass
    if len(params) != 1 or not issubclass(params[0].annotation, BaseModel):
        raise TypeError(
            f"{func.__name__}: must take exactly one parameter of type BaseModel"
        )
    
    # Validation 2: docstring is mandatory (becomes visible by LLM description)
    docstring = (func.__doc__ or "").strip()
    if not docstring:
        raise ValueError(
            f"{func.__name__}: docstring is required"
        )
    
    # Reject docstrings shorter than 15 characters — LLM needs enough context to decide.
    if len(docstring) < 15:
        raise ValueError(
            f"{func.__name__}: docstring too short ({len(docstring)} chars). "
            f"The LLM needs at least 15 characters to decide when to use the tool."
        )
    
    # Register: store func, Pydantic params model, and the description
    TOOL_REGISTRY[func.__name__] = {
        "func": func,
        "params_model": params[0].annotation,
        "description": docstring,
    }

    return func # the decorator returns the function unchanged