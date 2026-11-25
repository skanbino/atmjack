"""Tool registry -- name to callable, so the agent can dispatch."""
from __future__ import annotations

from. import scanner, creds, access

REGISTRY = {
 "scan": scanner.scan,
 "hydra": creds.hydra,
 "ldap_enum": access.ldap_enum,
}

def call(name: str, **kwargs):
 if name not in REGISTRY:
 raise KeyError(f"unknown tool: {name}")
 return REGISTRY[name](**kwargs)
