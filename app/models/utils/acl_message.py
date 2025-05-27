from dataclasses import dataclass
from typing import Any, Optional, Dict

@dataclass
class ACLMessage:
    performative: str
    sender: str
    content: Any = None
    receiver: Optional[str] = None
    language: Optional[str] = None
    encoding: Optional[str] = None
    ontology: Optional[str] = None
    protocol: Optional[str] = None
    conversation_id: Optional[str] = None
    reply_to: Optional[str] = None
    reply_with: Optional[str] = None
    in_reply_to: Optional[str] = None
    reply_by: Optional[str] = None
    
    def __init__(self, sender: str, content: Any, **kwargs) -> None:
        self.sender = sender
        self.content = content
        self.performative = kwargs.get('performative')
        self.receiver = kwargs.get('receiver')
        self.reply_to = kwargs.get('reply_to')
        self.language = kwargs.get('language')
        self.encoding = kwargs.get('encoding')
        self.ontology = kwargs.get('ontology')
        self.protocol = kwargs.get('protocol')
        self.conversation_id = kwargs.get('conversation_id')
        self.reply_with = kwargs.get('reply_with')
        self.in_reply_to = kwargs.get('in_reply_to')
        self.reply_by = kwargs.get('reply_by')
        
    def to_dict(self):
        return {
            'performative': self.performative,
            'sender': self.sender,
            'receiver': self.receiver,
            'content': self.content,
            'reply_to': self.reply_to,
            'language': self.language,
            'encoding': self.encoding,
            'ontology': self.ontology,
            'protocol': self.protocol,
            'conversation_id': self.conversation_id,
            'reply_with': self.reply_with,
            'in_reply_to': self.in_reply_to,
            'reply_by': self.reply_by
        }

        
    @classmethod
    def from_dict(cls, message_dict: Dict[str, Any]) -> "ACLMessage":
        """Creates an ACLMessage instance from a dictionary."""
        try:
            return cls(
                performative=message_dict['performative'],
                sender=message_dict['sender'],
                receiver=message_dict['receiver'],
                content=message_dict['content'],
                reply_to=message_dict.get('reply_to'),
                language=message_dict.get('language'),
                encoding=message_dict.get('encoding'),
                ontology=message_dict.get('ontology'),
                protocol=message_dict.get('protocol'),
                conversation_id=message_dict.get('conversation_id'),
                reply_with=message_dict.get('reply_with'),
                in_reply_to=message_dict.get('in_reply_to'),
                reply_by=message_dict.get('reply_by')
            )
        except KeyError as e:
            raise ValueError(f"Missing required field for ACLMessage: {e}")

    @staticmethod
    def validate_dict_message(message_dict: Dict[str, Any]) -> bool:
        """Validates if a dictionary has the required fields for an ACLMessage."""
        required_fields = ['performative', 'sender', 'receiver', 'content']
        for field in required_fields:
            if field not in message_dict:
                return False
        return True