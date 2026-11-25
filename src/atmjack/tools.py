from atmjack import access, creds, scanner

REGISTRY = {"scan": scanner.scan, "hydra": creds.hydra, "windapsearch": access.windapsearch}


def call(name: str, **kwargs):
    """Invoke a registered tool by name."""
    if name not in REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return REGISTRY[name](**kwargs)
