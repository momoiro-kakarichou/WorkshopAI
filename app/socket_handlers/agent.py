from pydantic import ValidationError

from app.extensions import socketio, log
from app.context import context
from app.dto.agent_dto import AgentCreateDTO, AgentUpdateDTO
from app.events import SocketIOEventType
from .common import socketio_unicast


@socketio.on(SocketIOEventType.AGENT_REQUEST)
def handle_agent_request(req_json):
    """Handles request for detailed agent information."""
    agent_id = req_json.get('id')
    if not agent_id:
        socketio_unicast(SocketIOEventType.AGENT, {'error': 'Agent ID is required.'})
        return

    try:
        agent_dto = context.agent_service.get_agent_full_info(agent_id=agent_id)
        if agent_dto:
            socketio_unicast(SocketIOEventType.AGENT, agent_dto.model_dump(mode='json'))
        else:
            socketio_unicast(SocketIOEventType.AGENT, {'error': f'Agent with ID {agent_id} not found.'})
    except Exception as e:
        log.exception(f"Error fetching agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT, {'error': f'An unexpected error occurred: {str(e)}'})


@socketio.on(SocketIOEventType.AGENT_LIST_REQUEST)
def handle_agent_list_request():
    """Handles request for the list of agents."""
    try:
        agent_list_dtos = context.agent_service.get_agent_list()
        agent_list = [dto.model_dump(mode='json') for dto in agent_list_dtos]
        socketio_unicast(SocketIOEventType.AGENT_LIST, {'agents': agent_list})
    except Exception as e:
        log.exception(f"Error fetching agent list: {e}")
        socketio_unicast(SocketIOEventType.AGENT_LIST, {'error': 'Failed to retrieve agent list.'})


@socketio.on(SocketIOEventType.AGENT_START_REQUEST)
def handle_agent_start_request(req_json):
    """Handles request to start an agent."""
    agent_id = req_json.get('id')
    if not agent_id:
        socketio_unicast(SocketIOEventType.AGENT_START, {'error': 'Agent ID is required.'})
        return

    try:
        success = context.agent_service.start_agent(agent_id=agent_id)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_START, {
                'message': 'success',
                'id': agent_id
            })
        else:
            error_msg = 'Failed to start agent.'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                     error_msg = f'Agent with ID {agent_id} not found.'
                elif agent_info.is_started:
                     error_msg = 'Agent is already started.'
            except Exception:
                log.warning(f"Could not retrieve agent info for {agent_id} during start failure.")

            socketio_unicast(SocketIOEventType.AGENT_START, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error starting agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_START, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })


@socketio.on(SocketIOEventType.AGENT_STOP_REQUEST)
def handle_agent_stop_request(req_json):
    """Handles request to stop an agent."""
    agent_id = req_json.get('id')
    if not agent_id:
        socketio_unicast(SocketIOEventType.AGENT_STOP, {'error': 'Agent ID is required.'})
        return

    try:
        success = context.agent_service.stop_agent(agent_id=agent_id)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_STOP, {
                'message': 'success',
                'id': agent_id
            })
        else:
            error_msg = 'Failed to stop agent.'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                     error_msg = f'Agent with ID {agent_id} not found.'
                elif not agent_info.is_started:
                     error_msg = 'Agent is not started.'
            except Exception:
                 log.warning(f"Could not retrieve agent info for {agent_id} during stop failure.")

            socketio_unicast(SocketIOEventType.AGENT_STOP, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error stopping agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_STOP, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })


@socketio.on(SocketIOEventType.AGENT_SAVE_REQUEST)
def handle_agent_save_request(req_json):
    """Handles request to save (create or update) an agent."""
    try:
        agent_id = req_json.get('id')

        if agent_id:
            update_dto = AgentUpdateDTO(**req_json)
            success = context.agent_service.update_agent(agent_id, update_dto)
            if success:
                socketio_unicast(SocketIOEventType.AGENT_SAVE, {
                    'message': 'success',
                    'id': agent_id
                })
            else:
                 socketio_unicast(SocketIOEventType.AGENT_SAVE, {
                    'error': f'Failed to update agent {agent_id}.',
                    'id': agent_id
                })
        else:
            create_dto = AgentCreateDTO(**req_json)
            created_agent_dto = context.agent_service.create_agent(create_dto)
            if created_agent_dto:
                socketio_unicast(SocketIOEventType.AGENT_SAVE, {
                    'message': 'success',
                    'id': created_agent_dto.id
                })
            else:
                socketio_unicast(SocketIOEventType.AGENT_SAVE, {
                    'error': 'Failed to create agent.'
                })
    except ValidationError as pve:
         log.error(f"DTO Validation error saving agent: {pve}")
         error_summary = "; ".join([f"{err['loc'][0] if err['loc'] else 'base'}: {err['msg']}" for err in pve.errors()])
         socketio_unicast(SocketIOEventType.AGENT_SAVE, {'error': f"Validation Error: {error_summary}"})
    except KeyError as ke:
         log.error(f"Missing key in agent save request: {ke}")
         socketio_unicast(SocketIOEventType.AGENT_SAVE, {'error': f"Missing required field: {ke}"})
    except Exception as e:
        log.exception(f"Error saving agent: {e}")
        socketio_unicast(SocketIOEventType.AGENT_SAVE, {
            'error': f'An unexpected error occurred: {str(e)}'
        })


@socketio.on(SocketIOEventType.AGENT_DELETE_REQUEST)
def handle_agent_delete_request(req_json):
    """Handles request to delete an agent."""
    agent_id = req_json.get('id')
    if not agent_id:
        socketio_unicast(SocketIOEventType.AGENT_DELETE, {'error': 'Agent ID is required.'})
        return

    try:
        success = context.agent_service.delete_agent(agent_id=agent_id)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_DELETE, {
                'message': 'success',
                'id': agent_id
            })
        else:
            error_msg = f'Failed to delete agent {agent_id}. It might have been running or an error occurred.'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                     error_msg = f'Agent with ID {agent_id} not found.'
            except Exception:
                 log.warning(f"Could not retrieve agent info for {agent_id} during delete failure.")

            socketio_unicast(SocketIOEventType.AGENT_DELETE, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error deleting agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_DELETE, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })


@socketio.on(SocketIOEventType.AGENT_NEW_VAR_REQUEST)
def handle_agent_new_variable(req_json):
    """Handles request to add a new variable to an agent."""
    agent_id = req_json.get('id')
    var_name = req_json.get('var_name')
    var_type = req_json.get('var_type')

    if not all([agent_id, var_name, var_type]):
        socketio_unicast(SocketIOEventType.AGENT_NEW_VAR, {'error': 'Missing required fields (id, var_name, var_type).'})
        return

    try:
        success = context.agent_service.add_agent_variable(agent_id, var_name, var_type)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_NEW_VAR, {
                'message': 'success',
                'id': agent_id,
                'var_name': var_name
            })
        else:
            error_msg = f'Failed to add variable "{var_name}".'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                    error_msg = f'Agent with ID {agent_id} not found.'
                elif var_name in agent_info.vars:
                     error_msg = f'Variable name "{var_name}" is already taken.'
            except Exception:
                 log.warning(f"Could not retrieve agent info for {agent_id} during add variable failure.")

            socketio_unicast(SocketIOEventType.AGENT_NEW_VAR, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error adding variable {var_name} to agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_NEW_VAR, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })


@socketio.on(SocketIOEventType.AGENT_IMPORT_VARS_REQUEST)
def handle_agent_import_variables(req_json):
    """Handles request to import variables, replacing existing ones."""
    agent_id = req_json.get('id')
    variables = req_json.get('variables')

    if not agent_id or variables is None:
        socketio_unicast(SocketIOEventType.AGENT_IMPORT_VARS, {'error': 'Missing required fields (id, variables).'})
        return

    if not isinstance(variables, dict):
        socketio_unicast(SocketIOEventType.AGENT_IMPORT_VARS, {
            'error': 'Invalid variables format. Expected a dictionary.',
            'id': agent_id
        })
        return

    try:
        success = context.agent_service.import_agent_variables(agent_id, variables)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_IMPORT_VARS, {
                'message': 'success',
                'id': agent_id
            })
        else:
            error_msg = 'Failed to import variables.'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                    error_msg = f'Agent with ID {agent_id} not found.'
            except Exception:
                 log.warning(f"Could not retrieve agent info for {agent_id} during import variables failure.")

            socketio_unicast(SocketIOEventType.AGENT_IMPORT_VARS, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error importing variables for agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_IMPORT_VARS, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })


@socketio.on(SocketIOEventType.AGENT_DELETE_VAR_REQUEST)
def handle_agent_delete_variable(req_json):
    """Handles request to delete a variable from an agent."""
    agent_id = req_json.get('id')
    var_name = req_json.get('var_name')

    if not all([agent_id, var_name]):
        socketio_unicast(SocketIOEventType.AGENT_DELETE_VAR, {'error': 'Missing required fields (id, var_name).'})
        return

    try:
        success = context.agent_service.delete_agent_variable(agent_id, var_name)
        if success:
            socketio_unicast(SocketIOEventType.AGENT_DELETE_VAR, {
                'message': 'success',
                'id': agent_id,
                'var_name': var_name
            })
        else:
            error_msg = f'Failed to delete variable "{var_name}".'
            try:
                agent_info = context.agent_service.get_agent_full_info(agent_id)
                if not agent_info:
                    error_msg = f'Agent with ID {agent_id} not found.'
                elif var_name not in agent_info.vars:
                     error_msg = f'Variable "{var_name}" not found.'
            except Exception:
                 log.warning(f"Could not retrieve agent info for {agent_id} during delete variable failure.")

            socketio_unicast(SocketIOEventType.AGENT_DELETE_VAR, {
                'error': error_msg,
                'id': agent_id
            })
    except Exception as e:
        log.exception(f"Error deleting variable {var_name} from agent {agent_id}: {e}")
        socketio_unicast(SocketIOEventType.AGENT_DELETE_VAR, {
            'error': f'An unexpected error occurred: {str(e)}',
            'id': agent_id
        })