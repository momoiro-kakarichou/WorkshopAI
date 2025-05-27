from flask import request
from app.extensions import socketio
from app.services import api_service
from app.context import context
from app.models import Node
from app.node_default_handlers import NODE_DEFAULT_INTERFACES
from app.events import SocketIOEventType
from .common import socketio_unicast
from app.utils.utils import create_logger
from app.dto.workflow_dto import (
    WorkflowSaveDTO, NodeDTO, LinkDTO, NodeUpdateDTO
)
from app.dao.workflow_dao import WorkflowDAO

wf_log = create_logger(__name__, entity_name='WORKFLOW_SOCKET', level=context.log_level)


@socketio.on(SocketIOEventType.WORKFLOW_REQUEST)
def handle_workflow_request(req_json):
    """Handles request for a single workflow's details."""
    workflow_id = req_json.get('id')
    if not workflow_id:
        socketio_unicast(SocketIOEventType.WORKFLOW, {'error': 'Workflow ID missing.'})
        return

    try:
        workflow_dto = context.workflow_service.get_workflow_detail(workflow_id)
        if workflow_dto:
            socketio_unicast(SocketIOEventType.WORKFLOW, workflow_dto.model_dump(mode='json'))
        else:
            socketio_unicast(SocketIOEventType.WORKFLOW, {'error': f'Workflow {workflow_id} not found.'})
    except Exception as e:
        wf_log.exception(f"Error fetching workflow {workflow_id}: {e}")
        socketio_unicast(SocketIOEventType.WORKFLOW, {'error': f'An unexpected error occurred: {str(e)}'})


@socketio.on(SocketIOEventType.WORKFLOW_LIST_REQUEST)
def handle_workflow_list_request():
    """Handles request for the list of workflows."""
    try:
        workflow_core_dtos = context.workflow_service.get_workflow_list()
        workflow_list = [dto.model_dump(mode='json') for dto in workflow_core_dtos]
        socketio_unicast(SocketIOEventType.WORKFLOW_LIST, {
            'workflows': workflow_list
        })
    except Exception as e:
        wf_log.exception(f"Error fetching workflow list: {e}")
        socketio_unicast(SocketIOEventType.WORKFLOW_LIST, {'error': 'Failed to retrieve workflow list.'})


@socketio.on(SocketIOEventType.WORKFLOW_SAVE_REQUEST)
def handle_workflow_save_request(req_json):
    """Handles saving (create/update) a workflow structure."""
    try:
        workflow_id = req_json.get('id')
        workflow_name = req_json.get('name')

        if not workflow_id and not workflow_name:
            raise ValueError("Workflow name is required when creating a new workflow.")

        save_dto = WorkflowSaveDTO(
            id=workflow_id,
            name=workflow_name,
            graph=req_json.get('graph'),
        )

        saved_workflow_core_dto = context.workflow_service.save_workflow(save_dto)

        if saved_workflow_core_dto:
            socketio_unicast(SocketIOEventType.WORKFLOW_SAVE, {
                'message': 'success',
                'id': saved_workflow_core_dto.id
            })
        else:
             socketio_unicast(SocketIOEventType.WORKFLOW_SAVE, {
                'message': 'error',
                'error': 'Failed to save workflow.'
            })

    except Exception as e:
        wf_log.exception(f"Error saving workflow: {e}")
        socketio_unicast(SocketIOEventType.WORKFLOW_SAVE, {
            'message': 'error',
            'error': str(e)
        })


@socketio.on(SocketIOEventType.WORKFLOW_DELETE_REQUEST)
def handle_workflow_delete_request(req_json):
    """Handles deleting a workflow."""
    workflow_id = req_json.get('id')
    if not workflow_id:
        socketio_unicast(SocketIOEventType.WORKFLOW_DELETE, {'message': 'error', 'error': 'Workflow ID missing.'})
        return

    try:
        success = context.workflow_service.delete_workflow(workflow_id)
        if success:
            socketio_unicast(SocketIOEventType.WORKFLOW_DELETE, {'message': 'success', 'id': workflow_id})
        else:
            socketio_unicast(SocketIOEventType.WORKFLOW_DELETE, {'message': 'error', 'error': f'Failed to delete workflow {workflow_id}. It might not exist or an error occurred.', 'id': workflow_id})
    except Exception as e:
        wf_log.exception(f"Error deleting workflow {workflow_id}: {e}")
        socketio_unicast(SocketIOEventType.WORKFLOW_DELETE, {'message': 'error', 'error': str(e), 'id': workflow_id})


@socketio.on(SocketIOEventType.NODE_GET_TYPES_REQUEST)
def handle_get_node_get_types_request():
    """Handles request for available node types."""
    try:
        node_types = Node.get_nodes_types()
        socketio_unicast(SocketIOEventType.NODE_GET_TYPES, {
            'message': 'success',
            'node_types': node_types
        })
    except Exception as e:
        wf_log.exception(f"Error getting node types: {e}")
        socketio_unicast(SocketIOEventType.NODE_GET_TYPES, {'message': 'error', 'error': str(e)})


@socketio.on(SocketIOEventType.NODE_GET_SUBTYPES_REQUEST)
def handle_get_node_get_subtypes_request(req_json: dict):
    """Handles request for available node subtypes for a given type."""
    node_type = req_json.get('node_type')
    try:
        node_subtypes = Node.get_nodes_subtypes_by_type(node_type)
        socketio_unicast(SocketIOEventType.NODE_GET_SUBTYPES, {
            'message': 'success',
            'node_subtypes': node_subtypes
        })
    except Exception as e:
        wf_log.exception(f"Error getting node subtypes for type {node_type}: {e}")
        socketio_unicast(SocketIOEventType.NODE_GET_SUBTYPES, {'message': 'error', 'error': str(e)})


@socketio.on(SocketIOEventType.NODE_SAVE_REQUEST)
def handle_node_save_request(req_json: dict):
    """Handles saving (create/update) a single node."""
    try:
        workflow_id = req_json.get('workflow_id')
        node_id = req_json.get('id')

        if not workflow_id:
             raise ValueError("workflow_id is required to save a node.")

        node_subtype = req_json.get('node_subtype')
        if node_subtype in NODE_DEFAULT_INTERFACES:
             default_interface = NODE_DEFAULT_INTERFACES[node_subtype]
             node_interface = {**(default_interface or {}), **req_json.get('interface', {})}
        else:
             node_interface = req_json.get('interface', {})

        print(req_json)

        saved_node_dto = None
        success = False
        if node_id:
            node_update_dto = NodeUpdateDTO(**req_json)
            if 'interface' in req_json or 'node_subtype' in req_json:
                 node_update_dto.interface = node_interface

            success = context.workflow_service.update_node(node_id, node_update_dto)
            if success:
                saved_node_dto = context.workflow_service.get_node_content(node_id)
        else:
            if not node_subtype:
                 raise ValueError("node_subtype is required when creating a new node.")
            node_dto = NodeDTO(
                name=req_json.get('name', 'Unnamed Node'),
                node_type=req_json.get('node_type', 'custom'),
                node_subtype=node_subtype,
                on=req_json.get('on', True),
                interface=node_interface,
                code=req_json.get('code', ''),
                handler=req_json.get('handler'),
                static_input=req_json.get('static_input', {}),
                workflow_id=workflow_id
            )
            saved_node_dto = context.workflow_service.add_node(workflow_id, node_dto)
            success = saved_node_dto is not None

        if success and saved_node_dto:
            socketio_unicast(SocketIOEventType.NODE_SAVE, {
                'message': 'success',
                'id': saved_node_dto.id
            })
        else:
            action = "update" if node_id else "add"
            error_message = f'Failed to {action} node.'
            if node_id and not saved_node_dto:
                 error_message = f'Node {node_id} updated, but failed to retrieve updated content.'

            socketio_unicast(SocketIOEventType.NODE_SAVE, {
                'message': 'error',
                'error': error_message,
                'id': node_id
            })

    except Exception as e:
        wf_log.exception(f"Error saving node: {e}")
        socketio_unicast(SocketIOEventType.NODE_SAVE, {
            'message': 'error',
            'error': str(e)
        })


@socketio.on(SocketIOEventType.NODE_DELETE_REQUEST)
def handle_node_delete_request(req_json):
    """Handles deleting a node."""
    node_id = req_json.get('id')

    if not node_id:
        socketio_unicast(SocketIOEventType.NODE_DELETE, {'message': 'error', 'error': 'Node ID missing.'})
        return

    try:
        success = context.workflow_service.delete_node(node_id)
        if success:
            socketio_unicast(SocketIOEventType.NODE_DELETE, {'message': 'success', 'id': node_id})
        else:
            socketio_unicast(SocketIOEventType.NODE_DELETE, {'message': 'error', 'error': f'Failed to delete node {node_id}. It might not exist.', 'id': node_id})
    except Exception as e:
        wf_log.exception(f"Error deleting node {node_id}: {e}")
        socketio_unicast(SocketIOEventType.NODE_DELETE, {
            'message': 'error',
            'error': str(e),
            'id': node_id
        })


@socketio.on(SocketIOEventType.NODE_CONTENT_REQUEST)
def handle_node_content_request(req_json):
    """Handles request for a single node's content."""
    node_id = req_json.get('id')

    if not node_id:
        socketio_unicast(SocketIOEventType.NODE_CONTENT, {'error': 'Node ID missing.'})
        return

    try:
        node_dto = context.workflow_service.get_node_content(node_id)
        if node_dto:
            socketio_unicast(SocketIOEventType.NODE_CONTENT, node_dto.model_dump(mode='json'))
        else:
            socketio_unicast(SocketIOEventType.NODE_CONTENT, {'error': f'Node {node_id} not found.'})
    except Exception as e:
        wf_log.exception(f"Error fetching node content for {node_id}: {e}")
        socketio_unicast(SocketIOEventType.NODE_CONTENT, {'error': f'An unexpected error occurred: {str(e)}'})


@socketio.on(SocketIOEventType.LINK_CREATE_REQUEST)
def handle_link_create_request(req_json):
    """Handles creating a link between nodes."""
    workflow_id = req_json.get('workflow_id')
    source_id = req_json.get('source')
    target_id = req_json.get('target')

    if not all([workflow_id, source_id, target_id]):
         socketio_unicast(SocketIOEventType.LINK_CREATE, {'message': 'error', 'error': 'Missing workflow_id, source, or target.'})
         return

    try:
        link_dto = LinkDTO(source=source_id, target=target_id)
        success = context.workflow_service.add_link(workflow_id, link_dto)
        if success:
            socketio_unicast(SocketIOEventType.LINK_CREATE, {'message': 'success'})
        else:
            socketio_unicast(SocketIOEventType.LINK_CREATE, {'message': 'error', 'error': 'Failed to create link. Check if nodes exist or link already exists.'})
    except Exception as e:
        wf_log.exception(f"Error creating link in workflow {workflow_id}: {e}")
        socketio_unicast(SocketIOEventType.LINK_CREATE, {
            'message': 'error',
            'error': str(e)
        })


@socketio.on(SocketIOEventType.LINK_DELETE_REQUEST)
def handle_link_delete_request(req_json):
    """Handles deleting a link between nodes."""
    workflow_id = req_json.get('workflow_id')
    source_id = req_json.get('source')
    target_id = req_json.get('target')

    if not all([workflow_id, source_id, target_id]):
         socketio_unicast(SocketIOEventType.LINK_DELETE, {'message': 'error', 'error': 'Missing workflow_id, source, or target.'})
         return

    try:
        link_dto = LinkDTO(source=source_id, target=target_id)
        success = context.workflow_service.delete_link(workflow_id, link_dto)
        if success:
            socketio_unicast(SocketIOEventType.LINK_DELETE, {'message': 'success'})
        else:
            socketio_unicast(SocketIOEventType.LINK_DELETE, {'message': 'error', 'error': 'Failed to delete link. Check if link exists.'})
    except Exception as e:
        wf_log.exception(f"Error deleting link in workflow {workflow_id}: {e}")
        socketio_unicast(SocketIOEventType.LINK_DELETE, {
            'message': 'error',
            'error': str(e)
        })

def get_openai_api_configs(workflow, node):
    """Provides options for OpenAI API configurations."""
    try:
        api_configs = api_service.get_api_ids_and_names(api_type='chat_completions')
        options = [{'value': config['id'], 'text': config['name']} for config in api_configs]
        return options
    except Exception as e:
        wf_log.error(f"Error fetching OpenAI API configs for node {node.id if node else 'unknown'}: {e}")
        return []

def get_standard_tool_names_options(workflow, node):
    """Provides options for standard tool names from ToolService."""
    try:
        tool_names = context.tool_service.get_standard_tool_names()
        options = [{'value': name, 'text': name} for name in sorted(tool_names)]
        return options
    except Exception as e:
        wf_log.error(f"Error fetching standard tool names for node {node.id if node else 'unknown'}: {e}")
        return []

def get_api_tags_options(workflow, node):
    """Provides options for API tags from ApiService."""
    try:
        tags = api_service.get_all_api_tags()
        options = [{'value': tag, 'text': tag} for tag in sorted(tags)]
        return options
    except Exception as e:
        wf_log.error(f"Error fetching API tags for node {node.id if node else 'unknown'}: {e}")
        return []

dynamic_options_providers = {
    'example_source_1': lambda workflow, node: [{'value': 'opt1', 'text': 'Option 1'}, {'value': 'opt2', 'text': 'Option 2'}],
    'example_source_2': lambda workflow, node: [{'value': 'valA', 'text': 'Value A'}, {'value': 'valB', 'text': 'Value B'}],
    'openai_api_configs': get_openai_api_configs,
    'standard_tool_names': get_standard_tool_names_options,
    'api_tags': get_api_tags_options,
}

@socketio.on(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS_REQUEST)
def handle_get_dynamic_options(data):
    """Handles requests for dynamic options for a node's SelectField."""
    workflow_id = data.get('workflow_id')
    node_id = data.get('node_id')
    options_source = data.get('options_source')
    sid = request.sid

    if not all([workflow_id, node_id, options_source]):
        socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {'message': 'error', 'error': 'Missing required parameters.', 'options_source': options_source}, room=sid)
        return


    temp_dao = WorkflowDAO()
    try:
        workflow = temp_dao.get_workflow_by_id(workflow_id, load_relations=True)
        if not workflow:
            socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {'message': 'error', 'error': 'Workflow not found.', 'options_source': options_source}, room=sid)
            return

        node = next((n for n in workflow.nodes if n.id == node_id), None)
        if not node:
            socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {'message': 'error', 'error': 'Node not found in workflow.', 'options_source': options_source}, room=sid)
            return

        provider_func = dynamic_options_providers.get(options_source)
        if not provider_func:
            socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {'message': 'error', 'error': f'No provider found for options source: {options_source}', 'options_source': options_source}, room=sid)
            return

        options = provider_func(workflow, node)
        if not isinstance(options, list):
            raise TypeError("Options provider did not return a list.")
        for option in options:
            if not isinstance(option, dict) or 'value' not in option or 'text' not in option:
                raise ValueError("Invalid option format returned by provider.")

        socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {
            'message': 'success',
            'options': options,
            'options_source': options_source
        }, room=sid)
        wf_log.debug(f"Successfully provided dynamic options for source '{options_source}' on node {node_id}")

    except Exception as e:
        wf_log.exception(f"Error getting dynamic options for source '{options_source}' on node {node_id}: {e}")
        socketio_unicast(SocketIOEventType.NODE_GET_DYNAMIC_OPTIONS, {'message': 'error', 'error': f'Error generating options: {e}', 'options_source': options_source}, room=sid)