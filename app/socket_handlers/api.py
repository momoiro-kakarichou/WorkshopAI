from app.extensions import socketio
from app.services import api_service
from app.dto.api_dto import ApiDTO
from app.events import SocketIOEventType
from .common import socketio_unicast

@socketio.on(SocketIOEventType.API_REQUEST)
def handle_api_request(req_json):
    api_id = req_json.get('id')
    if not api_id:
        socketio_unicast(SocketIOEventType.API, {'error': 'Missing API ID'}, success=False)
        return

    api_dto = api_service.get_api_by_id(id=api_id)
    if api_dto:
        socketio_unicast(SocketIOEventType.API, api_dto.model_dump(mode='json'))
    else:
        socketio_unicast(SocketIOEventType.API, {'error': f'API with id {api_id} not found'}, success=False)


@socketio.on(SocketIOEventType.API_LIST_REQUEST)
def handle_api_list_request(req_json):
    api_type = req_json.get('api_type')
    source = req_json.get('source')
    if not api_type or not source:
        socketio_unicast(SocketIOEventType.API_LIST, {'error': 'Missing api_type or source'}, success=False)
        return

    api_list_formatted = api_service.get_api_ids_and_names(api_type=api_type, source=source)
    socketio_unicast(SocketIOEventType.API_LIST, {'data': api_list_formatted, 'success': True})


@socketio.on(SocketIOEventType.API_SOURCE_REQUEST)
def handle_api_source_request(req_json):
    api_type = req_json.get('api_type')
    if not api_type:
        socketio_unicast(SocketIOEventType.API_SOURCE, {'error': 'Missing api_type'}, success=False)
        return

    api_sources = api_service.get_source_list(api_type=api_type)
    socketio_unicast(SocketIOEventType.API_SOURCE, {
        'api_sources': api_sources
    })


@socketio.on(SocketIOEventType.API_MODEL_REQUEST)
def handle_api_model_request(req_json):
    api_type = req_json.get('api_type')
    source = req_json.get('source')
    if not api_type or not source:
        socketio_unicast(SocketIOEventType.API_MODEL, {'error': 'Missing api_type or source'}, success=False)
        return

    api_models = api_service.get_models_list(api_type=api_type, source=source)
    socketio_unicast(SocketIOEventType.API_MODEL, {
        'api_models': api_models
    })


@socketio.on(SocketIOEventType.API_SAVE_REQUEST)
def handle_api_save_request(req_json):
    try:
        api_dto = ApiDTO(**req_json)
    except Exception as e:
        socketio_unicast(SocketIOEventType.API_SAVE, {'error': f'Invalid data format: {e}'}, success=False)
        return

    saved_dto = api_service.save_api(api_dto=api_dto)
    socketio_unicast(SocketIOEventType.API_SAVE, {'id': saved_dto.id, 'message': 'API saved successfully'})


@socketio.on(SocketIOEventType.API_DELETE_REQUEST)
def handle_api_delete_request(req_json):
    api_id = req_json.get('id')
    if not api_id:
        socketio_unicast(SocketIOEventType.API_DELETE, {'error': 'Missing API ID'}, success=False)
        return

    deleted = api_service.delete_api(api_id=api_id)
    if deleted:
        socketio_unicast(SocketIOEventType.API_DELETE, {'id': api_id, 'message': 'API deleted successfully'})
    else:
        socketio_unicast(SocketIOEventType.API_DELETE, {'error': f'API with id {api_id} not found or could not be deleted'}, success=False)


@socketio.on(SocketIOEventType.API_FETCH_EXTERNAL_MODELS_REQUEST)
def handle_api_fetch_external_models_request(req_json):
    api_url = req_json.get('api_url')
    api_key = req_json.get('api_key')
    api_type = req_json.get('api_type')

    if not api_url:
        socketio_unicast(SocketIOEventType.API_FETCH_EXTERNAL_MODELS_RESPONSE, {'error': 'Missing API URL'}, success=False)
        return

    try:
        models = api_service.fetch_external_models(api_url=api_url, api_key=api_key, api_type=api_type)
        socketio_unicast(SocketIOEventType.API_FETCH_EXTERNAL_MODELS_RESPONSE, {'models': models, 'success': True})
    except Exception as e:
        print(f"Error fetching external models: {e}")
        socketio_unicast(SocketIOEventType.API_FETCH_EXTERNAL_MODELS_RESPONSE, {'error': f'Failed to fetch models: {str(e)}'}, success=False)