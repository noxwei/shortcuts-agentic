"""Core types for the block composition system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class ParamDef:
    """Definition of a configurable block parameter."""

    type: str  # "str", "int", "float", "enum", "list[str]"
    default: Any = None
    choices: list[str] | None = None
    required: bool = False
    description: str = ""


@dataclass
class BlockContext:
    """Runtime context passed to a block's render function."""

    output_var: str  # The "as" name from the recipe
    params: dict[str, Any]  # Merged defaults + recipe params
    input_vars: dict[str, str]  # Maps input name -> actual variable name from wiring


class RenderFn(Protocol):
    def __call__(self, ctx: BlockContext) -> str: ...


@dataclass(frozen=True)
class Block:
    """A composable shortcut building block."""

    id: str
    category: str
    description: str
    includes: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    params: dict[str, ParamDef] = field(default_factory=dict)
    render: RenderFn = field(default=lambda ctx: "")

    def catalog_entry(self) -> str:
        """Generate a catalog line for the Gemma system prompt."""
        parts = [f"- {self.id}: {self.description}"]
        if self.params:
            param_strs = []
            for name, p in self.params.items():
                s = f"{name} ({p.type}"
                if p.choices:
                    s += f", one of: {'/'.join(p.choices)}"
                if p.required:
                    s += ", REQUIRED"
                s += ")"
                param_strs.append(s)
            parts.append(f"  Params: {', '.join(param_strs)}")
        if self.outputs:
            parts.append(f"  Outputs: {', '.join(self.outputs)}")
        return ". ".join(parts)


@dataclass
class ComposerResult:
    """Result of composing a recipe into Cherri source."""

    cherri_source: str = ""
    includes: list[str] = field(default_factory=list)
    block_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors
