from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal
from .context_block import ContextBlock
from app.constants import MessageRole


@dataclass
class ContextItem:
    content: ContextBlock
    role: str = MessageRole.NONE
    name: Optional[str] = None
    
    def to_dict(self):
        return {
            "content": self.content,
            "role": self.role
        }
    
@dataclass
class ContextManager:
    name: str
    relative_context_items: Dict[str, List[ContextItem]] = field(default_factory=lambda: {'before': [], 'after': []})
    absolute_context_items: Dict[str, List[ContextItem]] = field(default_factory=dict)
    
    def add_relative_context_item(self, context_item: ContextItem, position: Literal['before', 'after'], absolute_position: Optional[int] = None) -> None:
        if position in ['before', 'after']:
            if absolute_position is not None and isinstance(absolute_position, int):
                self.relative_context_items[position].insert(absolute_position, context_item)
            else:
                self.relative_context_items[position].append(context_item)
    
    def add_absolute_context_item(self, context_item: ContextItem, depth: int, absolute_position: Optional[int] = None) -> None:
        if isinstance(depth, int):
            if absolute_position is not None and isinstance(absolute_position, int):
                self.absolute_context_items.setdefault(str(depth), []).insert(absolute_position, context_item)
            else:
                self.absolute_context_items.setdefault(str(depth), []).append(context_item)
    
    def merge_same_role(self) -> None:       
        for position in ['before', 'after']:
            self.relative_context_items[position] = merge_context_items_by_role(self.relative_context_items[position])
        
        for depth in self.absolute_context_items:
            self.absolute_context_items[depth] = merge_context_items_by_role(self.absolute_context_items[depth])
    
    def resolve(self, chat_history: List[Dict]) -> List[ContextItem]:
        result_list = []
        result_list.extend(self.relative_context_items['before'])
        
        chat_length = len(chat_history)
        for i, message in enumerate(chat_history):
            context_block = ContextBlock(name=f"message_{i}", content=[message['content']])
            context_item = ContextItem(content=context_block, role=message['role'])
            result_list.append(context_item)
            
            depth_position = chat_length - i - 1
            if str(depth_position) in self.absolute_context_items:
                result_list.extend(self.absolute_context_items[str(depth_position)])
        
        result_list.extend(self.relative_context_items['after'])
        return result_list
    
    def flush(self) -> None:
        self.relative_context_items = {
            'before': [],
            'after': []
        }
        self.absolute_context_items = {}
        
def merge_context_items_by_role(context_items: List[ContextItem]) -> List[ContextItem]:
    if not context_items:
        return []
    
    merged_context_items = []
    current_context_item = context_items[0]
    
    for context_item in context_items[1:]:
        if context_item.role == current_context_item.role:
            current_context_item.content.insert_content(context_item.content, 'block_end')
        else:
            merged_context_items.append(current_context_item)
            current_context_item = context_item
    
    merged_context_items.append(current_context_item)
    return merged_context_items

def resolve_context_items_content(context_items: List[ContextItem]):
    for item in context_items:
        if isinstance(item.content, ContextBlock):
            item.content = item.content.resolve()