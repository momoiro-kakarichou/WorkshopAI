from dataclasses import dataclass, field
from typing import List, Union, TypeAlias, Literal, Optional
from .utils import StateMachine

ContextPositionType: TypeAlias = Literal[
    'block_start', 'block_end', 'after', 'before', 'depth'
]

@dataclass
class ContextBlock:
    name: str
    template: str = '{{content}}'
    content: List[Union['ContextBlock', StateMachine, str]] = field(default_factory=list)
    
    def insert_content(self, content: Union['ContextBlock', StateMachine, str],
                    position_type: ContextPositionType, position_value: Optional[Union[str, int]] = None) -> None:
        if len(self.content) == 0:
            self.content.append(content)
            return
        
        if position_type == 'block_start':
            self.content.insert(0, content)
        elif position_type == 'block_end':
            self.content.append(content)
        elif position_type == 'after':
            if position_value is not None:
                pass
            else:
                self.content.append(content)
        elif position_type == 'before':
            if position_value is not None:
                pass
            else:
                self.content.insert(0, content)
        elif position_type == 'depth':
            if position_value is not None and isinstance(position_value, int):
                self.content.insert(position_value, content)
            else:
                self.content.append(content)
        else:
            raise ValueError(f"Wrong position type '{position_type}' in context block '{self.name}'")
        
        
    def resolve_content(self) -> str:
        result_list = []
        for context_block in self.content:
            content = ''
            if isinstance(context_block, StateMachine):
                content = context_block.get_state_content()
            elif isinstance(context_block, str):
                content = context_block
            else:
                content = context_block.resolve()
            
            if content is not None and content != '':
                result_list.append(content)
        
        return '\n'.join(result_list)
    
    
    def resolve(self) -> str:
        content = self.resolve_content()
        return self.template.replace('{{content}}', content)