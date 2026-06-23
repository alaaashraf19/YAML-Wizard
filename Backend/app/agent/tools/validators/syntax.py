from __future__ import annotations

from typing import Any, Tuple, List, Dict

import yaml


def parse_yaml(yaml_content: str) -> Tuple[Any, List[Dict[str, Any]]]:
    try:
        doc = yaml.safe_load(yaml_content)
        return doc, []
    except yaml.YAMLError as exc:
        err: Dict[str, Any] = {
            "source": "pyyaml",
            "level": "syntax",
            "message": str(exc).strip().replace("\n", " | "),
        }
        mark = getattr(exc, "problem_mark", None) #location of the problem
        if mark is not None:
            err["line"] = mark.line + 1
            err["col"] = mark.column + 1
        problem = getattr(exc, "problem", None) #the specific thing that went wrong
        if problem:
            err["detail"] = problem
        context = getattr(exc, "context", None) #human‑readable phrase describing the part the parser was working on when it failed
        if context:
            err["context"] = context
        return None, [err]
