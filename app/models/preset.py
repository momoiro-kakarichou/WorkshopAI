# from dataclasses import dataclass, field
# from typing import List, Dict, Optional, Union, Any
# from app.utils.utils import *
# from app.utils.tokenizers import *
# from .chat import Chat


# @dataclass
# class Prompt:
#     name: str
#     role: str
#     position: str
#     depth: int
#     prompt: str
#     tokens: int = 0

#     def to_dict(self) -> Dict[str, Union[str, int]]:
#         return {
#             'name': self.name,
#             'role': self.role,
#             'position': self.position,
#             'depth': self.depth,
#             'prompt': self.prompt,
#             'tokens': self.tokens
#         }
    
#     def change_from_dict(self, data: Dict[str, Union[str, int]], model_group: str) -> None:
#         self.name = data.get('name', self.name)
#         self.role = data.get('role', self.role)
#         self.position = data.get('position', self.position)
#         self.depth = data.get('depth', self.depth)
#         self.prompt = data.get('prompt', self.prompt)
#         self.update_tokens(model_group)
    
#     def update_tokens(self, model_group: str) -> None:
#         self.tokens = count_tokens(model_group, self.prompt)
        

# @dataclass
# class Preset:
#     name: str
    
    
# @dataclass
# class Claude3Preset:
#     name: str
#     context_size: int
#     max_response_length: int
#     stream: bool
#     temperature: float
#     top_k: int
#     top_p: int
#     assistant_prefill: str
#     user_first_msg: str
#     prompts: List[Prompt]
#     creation_time: Optional[int] = None
#     id: Optional[str] = None

#     def __post_init__(self):
#         if not self.creation_time:
#             self.creation_time = int(time.time())
#         if not self.id:
#             self.id = f'{self.name}_{self.creation_time}'
    
#     def to_dict(self):
#         return {
#             "name": self.name,
#             "context_size": self.context_size,
#             "max_response_length": self.max_response_length,
#             "stream": self.stream,
#             "temperature": self.temperature,
#             "top_k": self.top_k,
#             "top_p": self.top_p,
#             "assistant_prefill": self.assistant_prefill,
#             "user_first_msg": self.user_first_msg,
#             "prompts": [prompt.to_dict() for prompt in self.prompts]
#         }
    
#     def add_prompt(self, name: str, role: str, position: int, depth: int, prompt: str):
#         self.prompts.append(Prompt(name=name, role=role, position=position,
#                                    depth=depth, prompt=prompt))
#         self.prompts[-1].update_tokens(model_group=CLAUDE3_MODEL_GROUP)
    
#     def get_prompt_by_number(self, number) -> Prompt:
#         return self.prompts[number]
        
#     def change_prompt_by_number(self, number: int, data: dict):
#         if number < len(self.prompts):
#             self.prompts[number].change_from_dict(data, model_group=CLAUDE3_MODEL_GROUP)
    
#     def remove_prompt_by_number(self, number: int):
#         del self.prompts[number]
    
#     def save_preset(self):
#         json_str = obj_to_json(self)
#         save_json(json_str, f'{PRESETS_PATH}/claude3_{self.id}.json')
    
#     def get_messages(self, chat: Chat) -> dict:
#         pass