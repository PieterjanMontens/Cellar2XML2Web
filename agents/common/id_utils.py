from ulid import ULID

def new_run_id(date_str: str) -> str:
    """Return sortable id: <YYYY-MM-DD>_<ULID>"""
    return f"{date_str}_{ULID()}"
