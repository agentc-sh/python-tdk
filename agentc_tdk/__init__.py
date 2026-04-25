from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import Any, Callable, ClassVar, cast


__tool_registry__: dict[str, type[Tool[Any, Any, Any]]] = {}
__args_coercers__: list[tuple[
    Callable[[type], bool],
    Callable[[type, dict[str, Any]], Any],
]] = [
    (lambda t: t is dict, lambda t, v: v),
    (lambda t: is_dataclass(t), lambda t, v: t(**{
        k: v for k, v in v.items()
        if k in {f.name for f in fields(t)}
    })),
    (lambda t: hasattr(t, "model_validate"), lambda t, v: (
        hasattr(t, "model_validate") and t.model_validate(v)
    )),
]
__state_coercers__: list[tuple[
    Callable[[type], bool],
    Callable[[type, dict[str, Any]], Any],
]] = [
    (lambda t: t is dict, lambda t, v: v),
    (lambda t: is_dataclass(t), lambda t, v: t(**{
        k: v for k, v in v.items()
        if k in {f.name for f in fields(t)}
    })),
    (lambda t: hasattr(t, "model_validate"), lambda t, v: (
        hasattr(t, "model_validate") and t.model_validate(v)
    )),
]
__result_coercers__: list[tuple[
    Callable[[type], bool],
    Callable[[type, Any], dict[str, Any]],
]] = [
    (lambda t: is_dataclass(t), lambda t, v: asdict(v)),
    (lambda t: hasattr(t, "model_dump"), lambda t, v: v.model_dump(mode="json")),
]

def _get_args_coercer(t: type) -> Callable[[dict[str, Any]], Any]:
    for check, coercer in __args_coercers__:
        if check(t):
            return lambda v: coercer(t, v)

    raise ValueError(f"No coercer found for type {t}")

def _get_state_coercer(t: type) -> Callable[[dict[str, Any]], Any]:
    for check, coercer in __state_coercers__:
        if check(t):
            return lambda v: coercer(t, v)

    raise ValueError(f"No state coercer found for type {t}")

def _get_result_coercer(t: type) -> Callable[[Any], dict[str, Any]]:
    for check, coercer in __result_coercers__:
        if check(t):
            return lambda v: coercer(t, v)

    raise ValueError(f"No coercer found for type {t}")

EmitFn = Callable[[str, list[dict[str, Any]]], None]

@dataclass
class ToolInput[TArgs, TState = None]:
    """
    Represents the input to a tool, containing the arguments required for execution.
    """
    args: TArgs
    state: TState | None = None
    emit: EmitFn | None = None

@dataclass
class ToolOutput[TResult]:
    """
    Represents the output of a tool, containing the result of execution and an optional
    state update.
    """
    output: TResult
    state_update: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the ToolOutput instance to a dictionary.

        :return: A dictionary representation of the ToolOutput instance.
        :rtype: dict[str, Any]
        """
        return {
            "output": _get_result_coercer(type(self.output))(self.output),
            "state_update": self.state_update,
        }

class Tool[TArgs, TResult, TState = None]:
    """
    A tool that can be executed with specific parameters and produces a result.

    :param args: The dataclass or Pydantic model type for the tool's input arguments.
    :type args: TArgs
    :param state: Optional type for the graph state snapshot the tool wants to receive.
    :type state: TState | None
    """
    args: type[TArgs]
    state: type[TState] | None = None

    name: ClassVar[str]
    description: ClassVar[str]
    schema: ClassVar[dict[str, Any]]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if hasattr(cls, "name"):
            __tool_registry__[cls.name] = cls

    def invoke(
        self,
        args: dict[str, Any],
        state: dict[str, Any] | None = None,
        emit: EmitFn | None = None
    ) -> Any:
        return (
            self.execute(
                ToolInput(
                    _get_args_coercer(self.args)(args),
                    state=cast(TState | None, (
                        _get_state_coercer(self.state)(state)
                        if state is not None and self.state is not None
                        else state
                    )),
                    emit=emit
                )
            )
            .to_dict()
        )

    def execute(self, input: ToolInput[TArgs, TState]) -> ToolOutput[TResult]:
        """
        Execute the tool with the given input and return the output.

        :param input: The input to the tool, containing the arguments required for execution.
        :type input: ToolInput[TArgs, TState]
        :return: The output of the tool, containing the result of execution and an
        optional state update.
        :rtype: ToolOutput[TResult]
        """
        raise NotImplementedError()

def get_tool_definition(name: str) -> dict[str, Any]:
    """
    Get the definition of a tool by its name.

    :param name: The name of the tool.
    :type name: str
    :return: A dictionary containing the name, description, and schema of the tool.
    :rtype: dict[str, Any]
    """
    cls = __tool_registry__[name]
    return {
        "name": cls.name,
        "description": cls.description,
        "schema": cls.schema,
    }

def invoke_tool(
    name: str,
    args: dict[str, Any],
    state: dict[str, Any] | None = None,
    emit: EmitFn | None = None
) -> dict[str, Any]:
    """
    Invoke a tool by its name with the given arguments.

    :param name: The name of the tool.
    :type name: str
    :param args: The arguments for the tool.
    :type args: dict[str, Any]
    :param state: The current graph state snapshot, passed through to the tool.
    :type state: dict[str, Any] | None
    :param emit: The function to emit events.
    :type emit: EmitFn | None
    :return: A dictionary containing the result of the tool execution.
    :rtype: dict[str, Any]
    """
    cls = __tool_registry__[name]
    return cls().invoke(args, state=state, emit=emit)
