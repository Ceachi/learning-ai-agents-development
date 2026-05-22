'''
PromptRegistry — loads YAML prompt templates and renders them with Jinja2.

Public API:
  - PromptTemplate         : immutable dataclass for a loaded YAML file
  - PromptRegistry         : loads / lists / renders / reloads templates
  - get_prompt_registry()  : lazy singleton, the only entry point used by callers
  - PromptReloadHandler    : watchdog handler that reloads on YAML edits

Side effect: importing this module starts a background daemon thread that
watches the prompts/ folder and auto-reloads the registry on any .yaml save.
'''

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Template
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Default folder where YAML prompts live, relative to the project root.
DEFAULT_PROMPTS_FOLDER = "prompts"


@dataclass(frozen=True)
class PromptTemplate:
    '''
    Immutable representation of one YAML prompt file.

    `frozen=True` prevents accidental mutation after loading: the template
    text is treated as configuration, not runtime state.

    Fields:
      - name, version, prompt : required.
      - description           : optional, one-line summary (developer-facing).
      - variables             : optional declared contract of expected variables.
                                None = no contract (anything goes);
                                ()   = declared empty (no variables allowed).
      - metadata              : optional dict (category, language, author, ...).
    '''
    name: str
    version: str
    prompt: str
    description: str = ""
    variables: tuple[str, ...] | None = None
    metadata: dict | None = None


class PromptRegistry:
    '''
    Catalog of PromptTemplate objects, keyed by `name`.

    Responsibilities:
      - Load every *.yaml file under `folder` into a typed PromptTemplate.
      - Render a template by name with Jinja2 variables.
      - Reload from disk on demand (used by the hot-reload watcher).
    '''

    def __init__(self, folder: str = DEFAULT_PROMPTS_FOLDER):
        self._folder = folder
        self._templates: dict[str, PromptTemplate] = self._load(folder)

    def _load(self, folder: str) -> dict[str, PromptTemplate]:
        '''Read every *.yaml file in `folder` and build a {name: PromptTemplate} dict.'''
        templates: dict[str, PromptTemplate] = {}
        for path in Path(folder).rglob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            # Distinguish "variables absent" (None -> no contract) from
            # "variables: []" (declared empty -> no variables allowed).
            raw_vars = data.get("variables")
            tpl = PromptTemplate(
                name=data["name"],
                version=data["version"],
                prompt=data["prompt"],
                description=data.get("description", ""),
                variables=tuple(raw_vars) if raw_vars is not None else None,
                metadata=data.get("metadata"),
            )
            if tpl.name in templates:
                raise ValueError(
                    f"Duplicate prompt name '{tpl.name}' found at {path}"
                )
            templates[tpl.name] = tpl
        return templates

    def get(self, name: str) -> PromptTemplate:
        '''Return the PromptTemplate registered under `name`, or raise KeyError.'''
        if name not in self._templates:
            raise KeyError(
                f"Prompt '{name}' not found. Available: {list(self._templates)}"
            )
        return self._templates[name]

    def render(self, name: str, **values) -> str:
        '''
        Render the prompt template `name` with the given values via Jinja2.

        If the template declares a `variables` contract, any value whose key is
        not in that contract raises ValueError BEFORE rendering — this catches
        typos (e.g. `max_word` instead of `max_words`) early, instead of
        silently producing a wrong prompt.

        Values referenced by the template but missing raise jinja2.UndefinedError
        unless the template provides a default via the `| default(...)` filter.
        '''
        template = self.get(name)
        if template.variables is not None:
            unknown = set(values) - set(template.variables)
            if unknown:
                raise ValueError(
                    f"Unknown variable(s) for prompt '{name}': {sorted(unknown)}. "
                    f"Declared variables: {list(template.variables)}"
                )
        return Template(template.prompt).render(**values)

    def list_templates(self) -> list[str]:
        '''Return all loaded template names.'''
        return list(self._templates.keys())

    def reload(self) -> None:
        '''Re-read every YAML file from disk. Used by PromptReloadHandler.'''
        self._templates = self._load(self._folder)


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    '''
    Lazy singleton accessor for the global PromptRegistry.

    `lru_cache` guarantees a single shared instance across the app —
    YAML files are read from disk only once per process.
    Call `get_prompt_registry().reload()` to refresh after editing files.
    '''
    return PromptRegistry(folder=DEFAULT_PROMPTS_FOLDER)


class PromptReloadHandler(FileSystemEventHandler):
    '''
    Watchdog handler that calls registry.reload() whenever a .yaml file
    under the prompts folder is modified. Used in development to pick up
    edits without restarting the process.
    '''

    def __init__(self, registry: PromptRegistry):
        self.registry = registry

    def on_modified(self, event):
        # Reload only when a .yaml file is modified
        if event.src_path.endswith(".yaml"):
            print(f"Detected modification: {event.src_path}. Reloading registry...")
            self.registry.reload()


# ---------------------------------------------------------------------------
# Hot reload setup — auto-runs at import time
# ---------------------------------------------------------------------------
# Starts a watchdog.Observer that triggers PromptRegistry.reload() whenever
# a .yaml file under prompts/ is modified. Now any save of a .yaml file
# → automatic reload.

registry = get_prompt_registry()
observer = Observer()
observer.schedule(
    PromptReloadHandler(registry),
    path=DEFAULT_PROMPTS_FOLDER,
    recursive=True,
)
observer.start()
