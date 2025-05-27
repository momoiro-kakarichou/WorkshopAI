from pydantic import ValidationError

from app.extensions import socketio, log
from app.events import SocketIOEventType
from .common import socketio_unicast
from app.services import card_service
from app.services.card_service import CardNotFoundError, CardServiceError
from app.dto.card_dto import CardCreateDTO, CardUpdateDTO

@socketio.on(SocketIOEventType.CARD_REQUEST)
def handle_card_request(req_json):
    """Handles request for a single card's details."""
    try:
        card_id = req_json['id']
        card_version = req_json.get('version')
        card_dto = card_service.get_card(card_id=card_id, version=card_version)
        socketio_unicast(SocketIOEventType.CARD, {
            'message': 'success',
            'card': card_dto.model_dump(mode='json'),
        })
    except CardNotFoundError as e:
        log.warning(f"Card not found handling card request: {e}")
        socketio_unicast(SocketIOEventType.CARD, {'error': str(e)})
    except KeyError as ke:
         log.error(f"Missing key in card request: {ke}")
         socketio_unicast(SocketIOEventType.CARD, {'error': f"Missing required field: {ke}"})
    except Exception as e:
        log.exception(f"Unexpected error handling card request: {e}")
        socketio_unicast(SocketIOEventType.CARD, {'error': f"An unexpected error occurred: {str(e)}"})


@socketio.on(SocketIOEventType.CARD_LIST_REQUEST)
def handle_cards_list_request():
    """Handles request for the list of available cards (basic info)."""
    try:
        card_basic_dtos = card_service.get_all_cards_basic_info()
        cards_list = [card.model_dump(mode='json') for card in card_basic_dtos]

        socketio_unicast(SocketIOEventType.CARD_LIST, {
            'cards': cards_list
        })
    except Exception as e:
        log.exception(f"Error handling card list request: {e}")
        socketio_unicast(SocketIOEventType.CARD_LIST, {
            'error': f"An error occurred while fetching the card list: {str(e)}"
        })


@socketio.on(SocketIOEventType.CARD_SAVE_REQUEST)
def handle_card_save_request(req_json):
    """Handles request to save (create or update) a card."""
    try:
        card_id = req_json.get('id')
        card_version = req_json.get('version')
        result_card_dto = None

        if card_id and card_version:
            log.info(f"Handler: Received update request for card {card_id}_{card_version}")
            update_dto = CardUpdateDTO(**req_json)
            result_card_dto = card_service.update_card(
                card_id=card_id,
                version=card_version,
                update_data=update_dto
            )
            log.info(f"Handler: Card {card_id}_{card_version} updated successfully.")

        else:
            log.info("Handler: Received create request for new card")
            create_dto = CardCreateDTO(**req_json)
            result_card_dto = card_service.create_card(card_data=create_dto)
            log.info(f"Handler: New card created successfully with ID {result_card_dto.id} Version {result_card_dto.version}.")

        socketio_unicast(SocketIOEventType.CARD_SAVE, {
            'message': 'success',
            'id': result_card_dto.id,
            'version': result_card_dto.version
        })

    except (CardNotFoundError, CardServiceError, ValueError) as ve:
         log.error(f"Service/Validation error saving card: {ve}")
         socketio_unicast(SocketIOEventType.CARD_SAVE, {'error': str(ve)})
    except ValidationError as pve:
         log.error(f"DTO Validation error saving card: {pve}")
         error_summary = "; ".join([f"{err['loc'][0] if err['loc'] else 'base'}: {err['msg']}" for err in pve.errors()])
         socketio_unicast(SocketIOEventType.CARD_SAVE, {'error': f"Validation Error: {error_summary}"})
    except KeyError as ke:
         log.error(f"Missing key in card save request: {ke}")
         socketio_unicast(SocketIOEventType.CARD_SAVE, {'error': f"Missing required field: {ke}"})
    except Exception as e:
        log.exception(f"Unexpected error handling card save request: {e}")
        socketio_unicast(SocketIOEventType.CARD_SAVE, {'error': "An unexpected server error occurred."})