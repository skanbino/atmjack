"""Small helpers shared across atmjack."""

from __future__ import annotations

from typing import Any

def fix_path_string(info: dict[str, Any], keys: list[str], path: str) -> str:
 return path.replace("/", ".")

def _resolve(info: Any, path: str) -> tuple[bool, Any]:
 current = info
 for part in path.split("."):
  if isinstance(current, dict):
   if part not in current:
    return False, None
   current = current[part]
  elif isinstance(current, list):
   try:
    index = int(part)
   except ValueError:
    return False, None
   if index >= len(current):
    return False, None
   current = current[index]
  else:
   return False, None
 return True, current

def _check(info: dict[str, Any], condition: dict[str, Any]) -> bool:
 found, value = _resolve(info, condition["path"])
 op = condition.get("op", "exists")
 if op == "exists":
  return found
 if not found:
  return False
 if op == "eq":
  return value == condition.get("value")
 if op == "ne":
  return value != condition.get("value")
 if op == "gt":
  return value > condition.get("value")
 if op == "lt":
  return value < condition.get("value")
 if op == "contains":
  return condition.get("value") in value
 return False

def pass_conditions(info: dict[str, Any], keys: list[str], conditions: Any) -> bool:
 if conditions is None:
  return True
 if isinstance(conditions, dict):
  conditions = [conditions]
 return all(_check(info, condition) for condition in conditions)

def get_keys(keys: list[str], cfg: Any, all_info: dict[str, Any] | None = None) -> list[str]:
 if all_info is None:
  return []
 results: list[str] = []

 def walk(node: Any, remaining: list[str], prefix: str) -> None:
  if not remaining:
   results.append(prefix)
   return
  head, rest = remaining[0], remaining[1:]
  if isinstance(node, dict):
   if head not in node:
    return
   walk(node[head], rest, f"{prefix}.{head}" if prefix else head)
  elif isinstance(node, list):
   for index, item in enumerate(node):
    walk(item, remaining, f"{prefix}.{index}" if prefix else str(index))

 walk(all_info, keys, "")
 return results