from typing import Any, Optional

from app.models.utils.acl_message import ACLMessage
from app.constants import ACLPerformative, DEFAULT_TOPIC
from app.models.utils.message_broker import MessageBroker

def handle_send_acl_message(
    agent_id: str,
    broker: MessageBroker,
    write_output,
    get_input,
    get_parent_output,
    *args, **kwargs
):
    """
    Handles sending an ACL message to a specified topic.
    The content is derived from parent node outputs.
    If there's a single parent output, its 'value' is used.
    Otherwise, the entire dictionary of parent outputs is used.
    The topic is read from the node's static input.
    """
    topic = get_input('topic', DEFAULT_TOPIC)
    if isinstance(topic, str):
        topic = topic.replace('/self', f'/agent:{agent_id}', 1)
    else:
        topic = DEFAULT_TOPIC
    parent_outputs = get_parent_output()
    content_to_send: Any

    if parent_outputs and len(parent_outputs) == 1:
        content_to_send = parent_outputs[0]
    else:
        content_to_send = {'key': 'aggregated_parent_outputs', 'value': parent_outputs}


    acl_msg_to_send = ACLMessage(
        sender=agent_id,
        performative=ACLPerformative.INFORM,
        content=content_to_send
    )

    if broker:
        broker.publish(topic, acl_msg_to_send)
        write_output('acl_message_sent', {'topic': topic, 'message': acl_msg_to_send.to_dict()})
    else:
        write_output('acl_message_sent', {'error': 'Broker not available', 'topic': topic})
        
def handle_extract_acl_content(
    get_input,
    write_output,
    write_raw_output,
    message: Optional[ACLMessage] = None,
    *args, **kwargs
):
    """
    Extracts content from an ACL message received by the node's 'message' input
    and writes it to the output
    """
    
    if not message:
        write_output('extracted_content', {'error': "No ACL message received in 'message' parameter"})
        return

    acl_content = None
    if isinstance(message, ACLMessage):
        acl_content = message.content
    elif isinstance(message, dict) and 'content' in message and 'sender' in message and 'performative' in message:
        acl_content = message.get('content')
    else:
        write_output('extracted_content', {'error': "Received 'message' is not a valid ACLMessage object or recognizable ACL dict.", 'received_type': str(type(message))})
        return

    write_raw_output(acl_content)