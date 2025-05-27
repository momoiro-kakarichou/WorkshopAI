# from dataclasses import dataclass
# from typing import List, Dict, Optional, Union, Any

# @dataclass
# class Entry:
#     keys: List[str]
#     content: str
#     extensions: Dict[str, Any]
#     enabled: bool
#     insertion_order: int
#     use_regex: bool
#     position: Optional[str]
    
#     name: Optional[str] = None
#     case_sensetive: Optional[bool] = None
#     constant: Optional[bool] = None
#     priority: Optional[int] = None
#     id: Optional[str] = None
#     comment: Optional[str] = None
#     selective: Optional[bool] = None
#     secondary_keys: Optional[List[str]] = None


# @dataclass
# class Lorebook:
#     spec: str
#     extensions: Dict[str, Any]
#     entries: List[Entry]
    
#     name: Optional[str] = None
#     description: Optional[str] = None
#     scan_depth: Optional[int] = None
#     token_budget: Optional[int] = None
#     recursive_scanning: Optional[bool] = None



class ContextEntry:
    rule: str # key/regex logic expression
    rule_type: str
    content: str # actually ContextBlock
    enabled: bool
    order: int
    position: str
    
    name: str