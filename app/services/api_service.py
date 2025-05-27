import json
import uuid
import requests
from typing import List, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.dao.api_dao import ApiDAO
from app.dto.api_dto import ApiDTO
from app.extensions import db
from app.utils.utils import load_json
from app.constants import API_CONFIGS_PATH

def get_api_config() -> dict:
    """Loads the API configuration from the JSON file."""
    try:
        json_str = load_json(f'{API_CONFIGS_PATH}/config.json')
        return json.loads(json_str)
    except FileNotFoundError:
            raise Exception(f"API config file not found at {API_CONFIGS_PATH}/config.json")
    except json.JSONDecodeError as e:
        raise Exception(f"Error decoding API config JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading API config: {str(e)}")

def get_source_list(api_type: str) -> list:
    """Retrieves the list of sources for a given API type from the config."""
    try:
        config = get_api_config()
        return config.get(api_type, [])
    except Exception as e:
        raise Exception(f"Error retrieving source list for type '{api_type}': {str(e)}")

def get_models_list(api_type: str, source: str) -> list:
    """Retrieves the list of models for a given API type and source from the config."""
    try:
        config = get_api_config()
        key = f'{api_type}_{source}'
        return config.get(key, [])
    except Exception as e:
        raise Exception(f"Error retrieving models list for type '{api_type}' and source '{source}': {str(e)}")

def get_api_by_id(id: str) -> Optional[ApiDTO]:
    """Retrieves an API configuration by ID and returns it as a DTO."""
    try:
        api_dao = ApiDAO.get_api_by_id(id)
        if api_dao:
            return ApiDTO.model_validate(api_dao)
        return None
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error retrieving API by ID '{id}': {str(e)}")

def get_api_list(api_type: str, source: str) -> List[ApiDTO]:
    """Retrieves a list of API configurations filtered by type and source, returned as DTOs."""
    try:
        api_dao_list = ApiDAO.get_api_list(api_type=api_type, source=source)
        return [ApiDTO.model_validate(api_dao) for api_dao in api_dao_list]
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error retrieving API list for type '{api_type}' and source '{source}': {str(e)}")

def get_api_ids_and_names(api_type: str, source: Optional[str] = None) -> List[Dict[str, str]]:
    """Retrieves API IDs and names filtered by type and optionally by source as a list of dictionaries."""
    try:
        results = ApiDAO.get_api_ids_and_names(api_type=api_type, source=source)
        return [{'id': id_, 'name': name} for id_, name in results]
    except Exception as e:
        db.session.rollback()
        source_info = f" and source '{source}'" if source else ""
        raise Exception(f"Error retrieving API IDs and names for type '{api_type}'{source_info}: {str(e)}")

def save_api(api_dto: ApiDTO) -> ApiDTO:
    """Saves an API configuration (creates or updates) based on the DTO."""
    try:
        api_data = api_dto.model_dump(exclude={'id'} if not api_dto.id else {})

        if api_dto.id:
            api_dao = ApiDAO.get_api_by_id(api_dto.id)
            if not api_dao:
                raise Exception(f"API with id {api_dto.id} not found for update.")
            ApiDAO.update_api_from_dict(api_dao, api_data)
            saved_api_dao = api_dao
        else:
            if 'id' not in api_data and not api_dto.id:
                    api_data['id'] = str(uuid.uuid4())
            elif api_dto.id:
                    api_data['id'] = api_dto.id

            saved_api_dao = ApiDAO.create_api(api_data)

        db.session.commit()
        db.session.refresh(saved_api_dao)
        return ApiDTO.model_validate(saved_api_dao)
    except SQLAlchemyError as e:
        db.session.rollback()
        raise Exception(f"Database error saving API: {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error saving API: {str(e)}")

def delete_api(api_id: str) -> bool:
    """Deletes an API configuration by its ID."""
    try:
        rows_affected = ApiDAO.delete_api_by_id(api_id)
        if rows_affected == 0:
                return False

        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        raise Exception(f"Database error deleting API ID '{api_id}': {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error deleting API ID '{api_id}': {str(e)}")

def get_apis_by_tag(tag: str, fallback_to_default: bool = False) -> List[ApiDTO]:
    """Retrieves a list of API configurations by tag, returned as DTOs.
    Optionally falls back to the 'default' tag if no APIs are found for the given tag.
    """
    try:
        api_dao_list = ApiDAO.get_apis_by_tag(tag)
        if not api_dao_list and fallback_to_default and tag != 'default':
            api_dao_list = ApiDAO.get_apis_by_tag('default')
        return [ApiDTO.model_validate(api_dao) for api_dao in api_dao_list]
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error retrieving APIs by tag '{tag}': {str(e)}")

def get_random_api_by_tag(tag: str, fallback_to_default: bool = False) -> Optional[ApiDTO]:
    """Retrieves a random API configuration by tag, returned as a DTO.
    Optionally falls back to the 'default' tag if no API is found for the given tag.
    """
    try:
        api_dao = ApiDAO.get_random_api_by_tag(tag)
        if not api_dao and fallback_to_default and tag != 'default':
            api_dao = ApiDAO.get_random_api_by_tag('default')
        
        if api_dao:
            return ApiDTO.model_validate(api_dao)
        return None
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error retrieving random API by tag '{tag}': {str(e)}")

def get_all_api_tags() -> List[str]:
    """Retrieves all distinct API tags from the database."""
    try:
        return ApiDAO.get_all_distinct_tags()
    except Exception as e:
        raise Exception(f"Error retrieving all API tags: {str(e)}")

def fetch_external_models(api_url: str, api_key: Optional[str] = None, api_type: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Fetches a list of models from an external API endpoint.
    Assumes the models endpoint is typically '/models' or '/v1/models' appended to the base api_url.
    """
    if not api_url:
        raise ValueError("API URL is required to fetch models.")

    if api_url.endswith('/'):
        models_endpoint = f"{api_url}models"
        v1_models_endpoint = f"{api_url}v1/models"
    else:
        models_endpoint = f"{api_url}/models"
        v1_models_endpoint = f"{api_url}/v1/models"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    models_list = []

    endpoints_to_try = [v1_models_endpoint, models_endpoint]
    
    for endpoint_url in endpoints_to_try:
        try:
            response = requests.get(endpoint_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                raw_models = data['data']
            elif isinstance(data, list):
                raw_models = data
            else:
                if endpoint_url == endpoints_to_try[-1]:
                    raise ValueError(f"Unexpected response format from {endpoint_url}. Expected a list of models or a dict with a 'data' key containing a list.")
                else:
                    continue

            for item in raw_models:
                if isinstance(item, dict) and 'id' in item:
                    models_list.append({'id': item['id'], 'name': item.get('name', item['id'])})
                elif isinstance(item, str):
                    models_list.append({'id': item, 'name': item})
            
            if models_list:
                return models_list

        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 404 and endpoint_url != endpoints_to_try[-1]:
                continue
            else:
                raise Exception(f"HTTP error fetching models from {endpoint_url}: {http_err}")
        except requests.exceptions.RequestException as req_err:
            if endpoint_url != endpoints_to_try[-1]:
                continue
            raise Exception(f"Request error fetching models from {endpoint_url}: {req_err}")
        except ValueError as val_err:
            if endpoint_url != endpoints_to_try[-1]:
                continue
            raise Exception(f"Error processing response from {endpoint_url}: {val_err}")

    if not models_list:
        raise Exception("Could not fetch models from any attempted endpoint or no models found.")
    
    return models_list