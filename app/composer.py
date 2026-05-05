"""Composer engine — takes a JSON recipe and produces valid Cherri source code."""

from __future__ import annotations

import json
from typing import Any

from app.block_registry import get_block
from blocks._meta import VALID_COLORS, VALID_GLYPHS
from blocks.schema import BlockContext, ComposerResult


def compose(recipe: dict[str, Any]) -> ComposerResult:
    """Take a JSON recipe, produce valid Cherri source code."""
    result = ComposerResult()
    errors = result.errors
    warnings = result.warnings

    # --- Validate top-level fields ---
    name = recipe.get("name", "").strip()
    if not name:
        errors.append("Recipe missing 'name'")
        name = "Untitled"

    icon = recipe.get("icon", "gear")
    if icon not in VALID_GLYPHS:
        warnings.append(f"Unknown glyph '{icon}', using 'gear'")
        icon = "gear"

    color = recipe.get("color", "blue")
    if color not in VALID_COLORS:
        warnings.append(f"Unknown color '{color}', using 'blue'")
        color = "blue"

    block_specs = recipe.get("blocks", [])
    if not block_specs:
        errors.append("Recipe has no blocks")
        return result

    # --- Resolve blocks and build variable scope ---
    includes: set[str] = set()
    scope: dict[str, str] = {}  # logical name -> actual Cherri variable name
    code_lines: list[str] = []

    for i, spec in enumerate(block_specs):
        block_id = spec.get("block", "")
        block = get_block(block_id)
        if block is None:
            errors.append(f"Block {i}: unknown block '{block_id}'")
            continue

        output_var = spec.get("as", f"_block{i}")
        params = dict(spec.get("params", {}))

        # Merge defaults from block definition
        for pname, pdef in block.params.items():
            if pname not in params and pdef.default is not None:
                params[pname] = pdef.default

        # Check required params
        for pname, pdef in block.params.items():
            if pdef.required and pname not in params:
                errors.append(f"Block {i} ({block_id}): missing required param '{pname}'")

        # Collect includes
        for inc in block.includes:
            includes.add(inc)

        # Build input variable mapping
        input_vars: dict[str, str] = {}
        # Explicit "input" param -> resolve from scope
        input_ref = params.get("input", "")
        if input_ref and isinstance(input_ref, str):
            if input_ref in scope:
                input_vars["input"] = scope[input_ref]
            else:
                input_vars["input"] = input_ref  # pass through, might be a direct var name
        # Also resolve any {var} references in prompt strings
        for pname, pval in params.items():
            if isinstance(pval, str):
                # Find all {ref} patterns and map them
                import re
                for ref in re.findall(r"\{(\w+)\}", pval):
                    if ref in scope:
                        input_vars[ref] = scope[ref]

        # Set implicit "default" input to previous block's output
        if i > 0 and "default" not in input_vars:
            prev_spec = block_specs[i - 1]
            prev_as = prev_spec.get("as", f"_block{i-1}")
            input_vars["default"] = prev_as

        # Render the block
        ctx = BlockContext(output_var=output_var, params=params, input_vars=input_vars)
        try:
            rendered = block.render(ctx)
            if rendered:
                code_lines.append(rendered)
        except Exception as e:
            errors.append(f"Block {i} ({block_id}): render failed: {e}")
            continue

        # Register outputs in scope
        scope[output_var] = output_var
        for out in block.outputs:
            # Multi-output blocks use output_var_suffix pattern
            full_name = f"{output_var}_{out}" if out != block.outputs[0] else output_var
            scope[f"{output_var}_{out}"] = f"{output_var}_{out}"
            if out not in scope:
                scope[out] = f"{output_var}_{out}" if len(block.outputs) > 1 else output_var

    if errors:
        return result

    # --- Assemble Cherri source ---
    header_lines = [
        f"#define name {name}",
        f"#define glyph {icon}",
        f"#define color {color}",
        "",
    ]

    include_lines = [f"#include '{inc}'" for inc in sorted(includes)]
    if include_lines:
        include_lines.append("")

    cherri = "\n".join(header_lines + include_lines + code_lines) + "\n"

    result.cherri_source = cherri
    result.includes = sorted(includes)
    result.block_count = len(block_specs)

    return result


def compose_from_json(json_str: str) -> ComposerResult:
    """Parse a JSON string recipe and compose it."""
    try:
        recipe = json.loads(json_str)
    except json.JSONDecodeError as e:
        result = ComposerResult()
        result.errors.append(f"Invalid JSON: {e}")
        return result
    return compose(recipe)
