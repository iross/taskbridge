"""YAML frontmatter edits that leave every key they don't touch exactly as written.

Rewriting a whole frontmatter block through a YAML dumper reorders, requotes and
reflows keys that other tools (backlog.md, Obsidian) wrote; these helpers only
replace the lines of the key being changed.
"""

import yaml

FENCE = "---\n"
_CLOSING = "\n---\n"


class FrontmatterError(ValueError):
    """A file's frontmatter is unterminated or not valid YAML."""


def split(text: str) -> tuple[list[str] | None, str]:
    """Frontmatter lines (without fences) and the body; None if the file has no frontmatter."""
    if not text.startswith(FENCE):
        return None, text
    end = text.find(_CLOSING, len(FENCE) - 1)
    if end < 0:
        raise FrontmatterError("unterminated frontmatter")
    inner = text[len(FENCE) : end]
    return (inner.split("\n") if inner else []), text[end + len(_CLOSING) :]


def load(lines: list[str]) -> dict:
    """Parse frontmatter lines into a dict."""
    try:
        data = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError as e:
        raise FrontmatterError(f"invalid frontmatter: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter is not a mapping")
    return data


def _is_key_line(line: str, key: str) -> bool:
    return not line.startswith((" ", "-")) and line.split(":", 1)[0] == key


def set_list(lines: list[str], key: str, values: list[str]) -> list[str]:
    """Replace `key` with a block-style list of `values`, in place, or append it."""
    if values:
        dumped = yaml.safe_dump(values, default_flow_style=False, allow_unicode=True, width=1000)
        block = [f"{key}:"] + ["  " + item for item in dumped.splitlines()]
    else:
        block = [f"{key}: []"]
    result: list[str] = []
    replaced = False
    in_key = False
    for line in lines:
        if _is_key_line(line, key):
            in_key = True
            if not replaced:
                result.extend(block)
                replaced = True
            continue
        if in_key and line.startswith((" ", "- ")):
            continue
        in_key = False
        result.append(line)
    return result if replaced else result + block


def join(lines: list[str], body: str) -> str:
    """Reassemble a file from frontmatter lines and body."""
    return FENCE + "".join(line + "\n" for line in lines) + "---\n" + body
