from typing import Dict, Optional, Any, Union, List
from app.constants import DEFAULT_TOPIC
from .general import ResourceNode, ActionNode, GeneratorNode

class NodeInterfaceField:
    """Base class for defining a node interface field."""
    def __init__(self, field_type: str, label: Optional[str] = None, description: Optional[str] = None, default: Any = None):
        self.type = field_type
        self.label = label
        self.description = description
        self.default = default

    def to_dict(self) -> Dict[str, Any]:
        """Converts the field definition to a dictionary."""
        data = {'type': self.type}
        if self.label is not None:
            data['label'] = self.label
        if self.description is not None:
            data['description'] = self.description
        if self.default is not None:
            data['default'] = self.default
        return data

class TextField(NodeInterfaceField):
    """Defines a text input field."""
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, default: str = '', placeholder: Optional[str] = None):
        super().__init__('text', label, description, default)
        self.placeholder = placeholder

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.placeholder is not None:
            data['placeholder'] = self.placeholder
        return data

class TextAreaField(NodeInterfaceField):
    """Defines a textarea input field."""
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, default: str = '', placeholder: Optional[str] = None, rows: int = 3):
        super().__init__('textarea', label, description, default)
        self.placeholder = placeholder
        self.rows = rows

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.placeholder is not None:
            data['placeholder'] = self.placeholder
        data['rows'] = self.rows
        return data

class NumberField(NodeInterfaceField):
    """Defines a number input field."""
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, default: Union[int, float] = 0, step: Union[int, float, str] = 'any'):
        super().__init__('number', label, description, default)
        self.step = step

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['step'] = self.step
        return data

class CheckboxField(NodeInterfaceField):
    """Defines a checkbox input field."""
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, default: bool = False):
        super().__init__('checkbox', label, description, default)

class SelectField(NodeInterfaceField):
    """Defines a select dropdown field."""
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None, default: Optional[str] = None, options: Optional[List[Union[str, Dict[str, str]]]] = None, options_source: Optional[str] = None):
        super().__init__('select', label, description, default)
        self.options = options if options is not None else []
        self.options_source = options_source

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['options'] = self.options
        if self.options_source is not None:
            data['options_source'] = self.options_source
        return data

def generate_interface_dict(*args: NodeInterfaceField, **kwargs: NodeInterfaceField) -> Dict[str, Dict[str, Any]]:
    """
    Generates the interface dictionary from NodeInterfaceField instances.
    Requires field names to be passed as keyword arguments.
    """
    interface = {}
    for key, field in kwargs.items():
        if isinstance(field, NodeInterfaceField):
            interface[key] = field.to_dict()
        else:
            raise TypeError(f"Value for key '{key}' must be an instance of NodeInterfaceField.")

    if args:
        raise ValueError("Using positional arguments is not supported. Please provide fields as keyword arguments (e.g., field_name=TextField(...)).")

    return interface

NODE_DEFAULT_INTERFACES: Dict[str, Optional[Dict[str, Dict[str, Any]]]] = {
    ResourceNode.CHAT_HISTORY: None,
    ActionNode.SQUASH_HISTORY: generate_interface_dict(
        separator=SelectField(
            label='Separator',
            description='Choose the separator to use between squashed messages of the same role.',
            default='\\n',
            options=[
                {'value': '\\n', 'text': 'Newline'},
                {'value': '\\n\\n', 'text': 'Double Newline'},
                {'value': ' ', 'text': 'Space'},
                {'value': '', 'text': 'None'}
            ]
        )
    ),
    ActionNode.CONVERT_TO_OPENAI_HISTORY: None,
    ActionNode.EXECUTE_TOOL_CALL: None,
    ActionNode.APPEND_TOOL_RESULTS_TO_HISTORY: None,
    GeneratorNode.OPENAI_CHAT_COMPLETION_STREAM: generate_interface_dict(
        api_tag=SelectField(
            label='API Tag',
            description='Select the API tag to use. A random API with this tag will be chosen.',
            options_source='api_tags'
        ),
        max_tokens=NumberField(label='Max Tokens', description='Maximum number of tokens to generate.', default=1024, step=1),
        temperature=NumberField(label='Temperature', description='Sampling temperature (0.0 to 2.0). Higher values make output more random.', default=1.0, step=0.1),
        top_p=NumberField(label='Top P', description='Nucleus sampling parameter (0.0 to 1.0).', default=1.0, step=0.1),
        stop_sequences=TextAreaField(label='Stop Sequences', description='JSON array of sequences to stop generation (e.g., ["stop1", "another sequence", "\\\\n"]).', default='[]', rows=3),
        stream=CheckboxField(
            label='Stream Response',
            description='Enable streaming for the response. If disabled, the full response will be returned at once.',
            default=True
        ),
        helper_function_name=SelectField(
            label='Helper Function',
            description='Optional helper function to process stream events.',
            options=[
                {'value': 'openai_stream_to_chat_add', 'text': 'Stream to Chat (Add Message)'},
                {'value': 'openai_stream_to_chat_swipe', 'text': 'Stream to Chat (Swipe Message)'},
                {'value': 'openai_stream_to_chat_append', 'text': 'Stream to Chat (Append to Message)'},
                {'value': 'None', 'text': 'None'}
            ],
            default='None'
        ),
        extra_params=TextAreaField(label='Extra Parameters (JSON)', description='Additional parameters to pass to the OpenAI API as a JSON object.', default='{}', rows=5)
    ),
    ActionNode.REGISTER_STANDARD_TOOL: generate_interface_dict(
        tool_name=SelectField(
            label='Standard Tool Name',
            description='Select the standard tool to register for use.',
            options_source='standard_tool_names'
        )
    ),
    ActionNode.DELETE_STANDARD_TOOL: generate_interface_dict(
        tool_name=SelectField(
            label='Standard Tool Name',
            description='Select the standard tool to deregister (decrement count).',
            options_source='standard_tool_names'
        )
    ),
    ResourceNode.GET_TOOL_SCHEMAS: generate_interface_dict(
        convert_to=SelectField(
            label='Schema Format',
            description='Select the desired format for the tool schemas.',
            default='OpenAI',
            options=[
                {'value': 'OpenAI', 'text': 'OpenAI Function Calling'}
            ]
        )
    ),
    ActionNode.SEND_ACL_MESSAGE: generate_interface_dict(
        topic=TextField(
            label='Topic',
            description='The topic to publish the ACL message to.',
            default=DEFAULT_TOPIC
        )
    ),
    ActionNode.EXTRACT_ACL_CONTENT: None,
    ActionNode.REGISTER_CUSTOM_TOOL: generate_interface_dict(
        tool_name=TextField(
            label='Custom Tool Name',
            description='Enter a unique name for your custom tool.',
            placeholder='my_custom_tool'
        ),
        tool_schema=TextAreaField(
            label='Tool Schema (JSON)',
            description='Enter the JSON schema for the tool (OpenAI function calling format). The function name will be automatically set from "Custom Tool Name".',
            default='{\n  "type": "function",\n  "function": {\n    "name": "your_tool_name_here",\n    "description": "A brief description of what this tool does.",\n    "parameters": {\n      "type": "object",\n      "properties": {\n        "param1": {\n          "type": "string",\n          "description": "Description of the first parameter."\n        }\n      },\n      "required": ["param1"]\n    }\n  }\n}',
            rows=12
        ),
        tool_function=TextAreaField(
            label='Tool Function (Python Code)',
            description='Write the Python function to execute for this tool. It will receive arguments as defined in the schema. For clarity and to ensure modules are correctly scoped, place import statements (standard library, project, or third-party) directly inside the function body. CAUTION: This code runs with fewer restrictions; ensure it is safe and trusted.',
            default='# Ensure your function accepts arguments as defined in your schema.\n# It is recommended to place imports inside the function.\n# Example:\ndef my_tool_function(param_name):\n    import json  # Standard library import\n    # from app.utils.utils import create_logger # Example project import\n\n    # logger = create_logger(__name__) # Using an imported utility\n    # logger.info(f"Tool executed with: {param_name}")\n    print(f"Tool executed with: {param_name}")\n    return {"result": f"Processed {param_name}"}\n\n# pass # Replace with your function code, ensuring it defines the function named in "Custom Tool Name".',
            rows=15
        )
    ),
    ActionNode.DELETE_CUSTOM_TOOL: generate_interface_dict(
        tool_name=TextField(
            label='Custom Tool Name',
            description='Enter the name of the custom tool to delete.',
            placeholder='my_custom_tool_to_delete'
        )
    )
}