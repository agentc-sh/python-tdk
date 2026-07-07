# agentc Python TDK

Types for writing [agentc](https://agentc.sh) tools in Python. agentc compiles tools written
against this package into the agent binary at build time, running them in an embedded Python
interpreter (RustPython), which supports pure-Python packages only.

## Installation

This package is not published to PyPI. Add it directly from git:

```bash
uv add git+https://github.com/agentc-sh/python-tdk
```

Pin a specific tag or commit for reproducible builds:

```bash
uv add git+https://github.com/agentc-sh/python-tdk --tag v0.1.0
uv add git+https://github.com/agentc-sh/python-tdk --rev <commit-sha>
```

If your tool package was scaffolded with `agentc tool init <name> --language python`, the
dependency is already configured for you.

## Quick start

A tool is a class with a `name`, a `description`, a JSON Schema for its inputs, and an `execute`
method. Subclass `Tool`, whose generic parameters are the argument type, the result type, and the
state type:

```python
from dataclasses import dataclass
from agentc_tdk import Tool, ToolInput, ToolOutput


@dataclass
class GetWeatherParams:
    location: str

@dataclass
class GetWeatherResult:
    temperature: float
    description: str


class GetWeatherTool(Tool[GetWeatherParams, GetWeatherResult, None]):
    args = GetWeatherParams

    name = "get_weather"
    description = "Get the current weather for a given location."
    schema = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "The location to get the weather for."},
        },
        "required": ["location"],
    }

    def execute(self, input: ToolInput[GetWeatherParams, None]) -> ToolOutput[GetWeatherResult]:
        return ToolOutput(
            output=GetWeatherResult(temperature=72.0, description=f"Sunny in {input.args.location}")
        )
```

A single package can define as many tool classes as it needs.

## Writing back to state

A tool can return a `state_update` alongside its output: a list of
[RFC 6902 JSON Patch](https://jsonpatch.com/) operations that are applied to the agent's state and
streamed to the client as state delta events.

```python
def execute(self, input: ToolInput[GetWeatherParams, None]) -> ToolOutput[GetWeatherResult]:
    return ToolOutput(
        output=GetWeatherResult(temperature=72.0, description="Sunny"),
        state_update=[
            {"op": "add", "path": "/context/last_location", "value": input.args.location}
        ],
    )
```

A tool can also call the `emit` function passed on `ToolInput` to send stateless activity events
to the client in real time, useful for generative UI.

## Declaring the tool in a manifest

Once written, point a `tool` block at the package directory in your agent's manifest:

```hcl title="agent.acl"
tool "get_weather" {
  kind   = "python"
  source = "./weather"
}
```

See the [agentc documentation](https://agentc.sh/docs) for the full guide to writing and
declaring tools.

## Development

This repo uses [uv](https://docs.astral.sh/uv/) and [Task](https://taskfile.dev).

```bash
uv sync
task python:build
task python:lint
task python:fmt
task python:test
```

## License

MIT
