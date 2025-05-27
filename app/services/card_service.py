import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.context import context
from app.dao.card_dao import CardDAO
from app.dto.card_dto import (CardDTO, CardBasicDTO, CardContextAssetDTO, CardFileAssetDTO,
                              CardCreateDTO, CardUpdateDTO, CardAssetCreateUpdateDTO)
from app.models.card import Card, CardContextAsset, CardFileAsset
from app.constants import CARDS_ASSETS_PATH, CARDS_ASSETS_ROUTE
from app.utils.utils import create_logger

card_service_log = create_logger(__name__, entity_name='CARD_SERVICE', level=context.log_level)

class CardServiceError(Exception):
    """Custom exception for card service errors."""
    pass

class CardNotFoundError(CardServiceError):
    """Exception raised when a card is not found."""
    pass

class AssetNotFoundError(CardServiceError):
    """Exception raised when an asset is not found."""
    pass

class FileOperationError(CardServiceError):
    """Exception raised during file system operations."""
    pass

# --- Helper Functions ---

def _get_card_asset_folder(card_id: str, card_version: str) -> str:
    """Returns the absolute path to the asset folder for a specific card version."""
    return os.path.join(CARDS_ASSETS_PATH, card_id, card_version)

def _get_file_asset_path(asset: CardFileAsset) -> str:
    """Gets the full path for a CardFileAsset."""
    return os.path.join(CARDS_ASSETS_PATH, asset.card_id, asset.card_version, asset.uri)

def _get_file_asset_url(asset: CardFileAsset) -> str:
    """Gets the web-accessible URL for a CardFileAsset."""
    return f"{CARDS_ASSETS_ROUTE}/{asset.card_id}/{asset.card_version}/{asset.uri}"

def _get_default_avatar_url() -> str:
    """Gets the URL for the default avatar."""
    return f'{CARDS_ASSETS_ROUTE}/default/avatar.png'

def _map_context_asset_model_to_dto(asset: CardContextAsset) -> CardContextAssetDTO:
    """Maps a CardContextAsset SQLAlchemy model to a DTO."""
    return CardContextAssetDTO.model_validate(asset)

def _map_file_asset_model_to_dto(asset: CardFileAsset) -> CardFileAssetDTO:
    """Maps a CardFileAsset SQLAlchemy model to a DTO."""
    dto = CardFileAssetDTO.model_validate(asset)
    dto.url = _get_file_asset_url(asset)
    return dto

def _map_card_model_to_dto(card: Card) -> CardDTO:
    """Maps a Card SQLAlchemy model to a full CardDTO."""
    context_asset_dtos = [_map_context_asset_model_to_dto(a) for a in card.context_assets]
    file_asset_dtos = [_map_file_asset_model_to_dto(a) for a in card.file_assets]
    agent_ids = [agent.id for agent in card.agents]
    chat_ids = [chat.id for chat in card.chats]

    return CardDTO(
        id=card.id,
        version=card.version,
        name=card.name,
        creator=card.creator,
        creator_note=card.creator_note,
        tags=card.tags,
        creation_date=card.creation_date,
        modification_date=card.modification_date,
        context_assets=context_asset_dtos,
        file_assets=file_asset_dtos,
        agents=agent_ids,
        chats=chat_ids
    )

def _map_card_model_to_basic_dto(card: Card) -> CardBasicDTO:
    """Maps a Card SQLAlchemy model to a CardBasicDTO."""
    avatar_asset = CardDAO.get_file_asset_by_tag(card.id, card.version, 'card_avatar')
    avatar_url = _get_file_asset_url(avatar_asset) if avatar_asset else _get_default_avatar_url()
    return CardBasicDTO(
        id=card.id,
        version=card.version,
        name=card.name,
        avatar_uri=avatar_url
    )

# --- Card Service Functions ---

def get_card(card_id: str, version: Optional[str] = None) -> CardDTO:
    """
    Retrieves a specific card version or the latest version if version is None.
    Raises CardNotFoundError if the card doesn't exist.
    """
    card_service_log.info(f"Service: Getting card id={card_id}, version={version or 'latest'}")
    if version:
        card = CardDAO.get_card_by_primary_key(card_id, version)
    else:
        card = CardDAO.get_latest_card_by_id(card_id)

    if not card:
        card_service_log.warning(f"Service: Card not found: id={card_id}, version={version or 'latest'}")
        raise CardNotFoundError(f"Card with ID {card_id} (Version: {version or 'latest requested'}) not found.")

    return _map_card_model_to_dto(card)

def get_all_cards_basic_info() -> List[CardBasicDTO]:
    """Retrieves basic information (id, version, name, avatar) for all cards (latest versions)."""
    card_service_log.info("Service: Getting basic info for all cards (latest versions)")
    all_cards = CardDAO.get_all_cards()
    latest_cards_map = {}
    for card in all_cards:
        if card.id not in latest_cards_map or card.modification_date > latest_cards_map[card.id].modification_date:
            latest_cards_map[card.id] = card

    return [_map_card_model_to_basic_dto(card) for card in latest_cards_map.values()]


def create_card(card_data: CardCreateDTO) -> CardDTO:
    """Creates a new card."""
    card_service_log.info(f"Service: Creating new card with name='{card_data.name}'")
    card_id = card_data.id or str(uuid.uuid4())
    version = card_data.version

    try:
        existing_card = CardDAO.get_card_by_primary_key(card_id, version)
        if existing_card:
            card_service_log.error(f"Service: Card with ID {card_id} and version {version} already exists.")
            raise CardServiceError(f"Card with ID {card_id} and version {version} already exists.")

        new_card = Card(
            id=card_id,
            version=version,
            name=card_data.name,
            creator=card_data.creator,
            creator_note=card_data.creator_note,
            tags=card_data.tags,
            creation_date=datetime.now(timezone.utc),
            modification_date=datetime.now(timezone.utc)
        )
        saved_card = CardDAO.save_card(new_card)
        db.session.commit()
        card_service_log.info(f"Service: Card created successfully: id={saved_card.id}, version={saved_card.version}")
        db.session.refresh(saved_card)
        return _map_card_model_to_dto(saved_card)
    except (SQLAlchemyError, CardServiceError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error creating card {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error creating card {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while creating the card: {e}")

def update_card(card_id: str, version: str, update_data: CardUpdateDTO) -> CardDTO:
    """Updates an existing card."""
    card_service_log.info(f"Service: Updating card id={card_id}, version={version}")
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            card_service_log.warning(f"Service: Card not found for update: id={card_id}, version={version}")
            raise CardNotFoundError(f"Card with ID {card_id} and version {version} not found.")

        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
             raise ValueError("No update data provided.")

        for key, value in update_dict.items():
            setattr(card, key, value)

        updated_card = CardDAO.update_card(card)
        db.session.commit()
        card_service_log.info(f"Service: Card updated successfully: id={updated_card.id}, version={updated_card.version}")
        db.session.refresh(updated_card)
        return _map_card_model_to_dto(updated_card)
    except (SQLAlchemyError, CardNotFoundError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error updating card {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error updating card {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while updating the card: {e}")

def delete_card(card_id: str, version: str) -> None:
    """Deletes a specific version of a card and its assets folder."""
    card_service_log.info(f"Service: Deleting card id={card_id}, version={version}")
    card_found = False
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            card_service_log.warning(f"Service: Card not found for deletion: id={card_id}, version={version}")
            raise CardNotFoundError(f"Card with ID {card_id} and version {version} not found.")
        card_found = True

        CardDAO.delete_card(card)
        db.session.commit()
        card_service_log.info(f"Service: Card record deleted successfully from DB: id={card_id}, version={version}")

    except (SQLAlchemyError, CardNotFoundError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error deleting card record {card_id}_{version} from DB: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error deleting card record {card_id}_{version} from DB: {e}")
        raise CardServiceError(f"An unexpected error occurred during DB deletion: {e}")

    # --- Physical File Deletion (outside DB transaction) ---
    if card_found:
        asset_folder = _get_card_asset_folder(card_id, version)
        folder_deleted = False
        if os.path.exists(asset_folder):
            try:
                shutil.rmtree(asset_folder)
                card_service_log.info(f"Service: Deleted asset folder: {asset_folder}")
                folder_deleted = True
            except Exception as e:
                card_service_log.error(f"Service: Failed to delete asset folder {asset_folder}: {e}")
                raise FileOperationError(f"DB record deleted, but failed to delete asset folder {asset_folder}: {e}")

        if folder_deleted:
            try:
                remaining_cards = CardDAO.get_cards_by_id(card_id)
                if not remaining_cards:
                    card_service_log.info(f"Service: No remaining versions for card {card_id}. Attempting base folder deletion.")
                    card_base_folder = os.path.join(CARDS_ASSETS_PATH, card_id)
                    if os.path.exists(card_base_folder):
                        if not os.listdir(card_base_folder):
                            os.rmdir(card_base_folder)
                            card_service_log.info(f"Service: Deleted empty base card folder: {card_base_folder}")
                        else:
                            card_service_log.warning(f"Service: Base card folder {card_base_folder} not empty, not deleting.")
            except SQLAlchemyError as e:
                 card_service_log.error(f"Service: DB error checking remaining cards for {card_id} after deletion: {e}")
            except Exception as e:
                card_service_log.error(f"Service: Failed during base card folder check/deletion for {card_id}: {e}")

    card_service_log.info(f"Service: Card deletion process completed for id={card_id}, version={version}")


def fork_card(card_id: str, existing_version: str, new_version: str) -> CardDTO:
    """Creates a fork of an existing card with a new version, copying assets."""
    card_service_log.info(f"Service: Forking card id={card_id} from version={existing_version} to {new_version}")
    if not new_version:
        raise ValueError("New version must be specified for forking.")

    forked_card_instance = None
    source_card = None
    cloned_file_assets = []
    try:
        source_card = CardDAO.get_card_by_primary_key(card_id, existing_version)
        if not source_card:
            card_service_log.warning(f"Service: Source card not found for fork: id={card_id}, version={existing_version}")
            raise CardNotFoundError(f"Source card with ID {card_id} and version {existing_version} not found.")

        existing_fork = CardDAO.get_card_by_primary_key(card_id, new_version)
        if existing_fork:
            card_service_log.error(f"Service: Target fork version already exists: id={card_id}, version={new_version}")
            raise CardServiceError(f"Card with ID {card_id} and version {new_version} already exists.")

        forked_card = Card(
            id=source_card.id,
            version=new_version,
            name=source_card.name,
            creator=source_card.creator,
            creator_note=source_card.creator_note,
            tags=source_card.tags.copy(),
            creation_date=datetime.now(timezone.utc),
            modification_date=datetime.now(timezone.utc)
        )
        forked_card_instance = CardDAO.save_card(forked_card)

        cloned_context_assets = []
        for asset in source_card.context_assets:
            cloned_asset = CardContextAsset(
                type=asset.type, tag=asset.tag, name=asset.name, ext=asset.ext,
                data=asset.data.copy(),
                card_id=forked_card.id, card_version=forked_card.version
            )
            cloned_context_assets.append(CardDAO.save_context_asset(cloned_asset))

        for asset in source_card.file_assets:
            cloned_asset = CardFileAsset(
                type=asset.type, tag=asset.tag, name=asset.name, ext=asset.ext,
                uri=asset.uri,
                card_id=forked_card.id, card_version=forked_card.version
            )
            cloned_file_assets.append(CardDAO.save_file_asset(cloned_asset))

        db.session.commit()
        card_service_log.info(f"Service: Card and asset records forked successfully in DB: id={forked_card_instance.id}, version={forked_card_instance.version}")
        db.session.refresh(forked_card_instance)
        for asset in cloned_context_assets:
            db.session.refresh(asset)
        for asset in cloned_file_assets:
            db.session.refresh(asset)

    except (SQLAlchemyError, CardNotFoundError, CardServiceError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error during database operations for forking card {card_id}_{existing_version} to {new_version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error during database operations for fork: {e}")
        raise CardServiceError(f"An unexpected error occurred during the database part of the fork: {e}")


    if not source_card or not forked_card_instance:
         card_service_log.error("Service: Fork failed before file operations could start.")
         raise CardServiceError("Fork process failed unexpectedly before file operations.")

    file_copy_errors = []
    source_folder = _get_card_asset_folder(card_id, existing_version)
    dest_folder = _get_card_asset_folder(card_id, new_version)

    if os.path.exists(source_folder):
        try:
            os.makedirs(dest_folder, exist_ok=True)
        except Exception as e:
             card_service_log.error(f"Service: Failed to create destination folder {dest_folder} for fork (DB changes committed): {e}")
             raise FileOperationError(f"DB records created, but failed to create destination folder {dest_folder}: {e}")

        for asset_record in cloned_file_assets:
            source_asset_origin = next((sa for sa in source_card.file_assets if sa.uri == asset_record.uri and sa.tag == asset_record.tag), None)
            if not source_asset_origin:
                 card_service_log.warning(f"Service: Could not find original source asset for cloned asset {asset_record.id} (uri: {asset_record.uri}). Skipping file copy.")
                 continue

            source_file_path = _get_file_asset_path(source_asset_origin)
            dest_file_path = _get_file_asset_path(asset_record)

            if os.path.exists(source_file_path):
                try:
                    os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                    shutil.copy2(source_file_path, dest_file_path)
                    card_service_log.debug(f"Service: Copied asset file from {source_file_path} to {dest_file_path}")
                except Exception as e:
                    card_service_log.error(f"Service: Failed to copy asset file {asset_record.uri} during fork (DB changes committed): {e}")
                    file_copy_errors.append(asset_record.uri)
            else:
                card_service_log.warning(f"Service: Source asset file not found during fork copy: {source_file_path}. DB record cloned, but file missing.")
                file_copy_errors.append(f"{asset_record.uri} (source missing)")

    if file_copy_errors:
        card_service_log.warning(f"Service: Fork completed for {card_id}_{new_version}, but some asset files failed to copy: {file_copy_errors}")

    card_service_log.info(f"Service: Card fork process completed for id={forked_card_instance.id}, version={forked_card_instance.version}")
    return _map_card_model_to_dto(forked_card_instance)


# --- Asset Service Functions ---

def add_context_asset(card_id: str, version: str, asset_data: CardAssetCreateUpdateDTO) -> CardContextAssetDTO:
    """Adds a new context asset to a card."""
    card_service_log.info(f"Service: Adding context asset to card={card_id}_{version}, tag={asset_data.tag}")
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            raise CardNotFoundError(f"Card {card_id}_{version} not found.")
        if asset_data.data is None:
            raise ValueError("Missing 'data' field for context asset.")

        asset = CardContextAsset(
            type=asset_data.type, tag=asset_data.tag, name=asset_data.name, ext=asset_data.ext,
            data=asset_data.data, card_id=card_id, card_version=version
        )
        saved_asset = CardDAO.save_context_asset(asset)
        CardDAO.update_card(card)
        db.session.commit()
        card_service_log.info(f"Service: Context asset added: id={saved_asset.id}")
        db.session.refresh(saved_asset)
        db.session.refresh(card)
        return _map_context_asset_model_to_dto(saved_asset)
    except (SQLAlchemyError, CardNotFoundError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error adding context asset to {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error adding context asset to {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while adding the context asset: {e}")

def add_file_asset(card_id: str, version: str, asset_data: CardAssetCreateUpdateDTO, file_content: Optional[bytes] = None) -> CardFileAssetDTO:
    """
    Adds a new file asset to a card.
    Requires asset_data.uri to be set.
    If file_content is provided, it writes the content to the corresponding path.
    """
    card_service_log.info(f"Service: Adding file asset to card={card_id}_{version}, tag={asset_data.tag}, uri={asset_data.uri}")
    saved_asset_instance = None
    card_instance = None
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            raise CardNotFoundError(f"Card {card_id}_{version} not found.")
        card_instance = card
        if not asset_data.uri:
            raise ValueError("Missing 'uri' field for file asset.")

        asset = CardFileAsset(
            type=asset_data.type, tag=asset_data.tag, name=asset_data.name, ext=asset_data.ext,
            uri=asset_data.uri, card_id=card_id, card_version=version
        )

        saved_asset_instance = CardDAO.save_file_asset(asset)
        CardDAO.update_card(card_instance)
        db.session.commit()
        card_service_log.info(f"Service: File asset record saved: id={saved_asset_instance.id}")
        db.session.refresh(saved_asset_instance)
        db.session.refresh(card_instance)

    except (SQLAlchemyError, CardNotFoundError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error saving file asset record for {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error saving file asset record for {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while saving the file asset record: {e}")

    # --- File Write Operation (Post-Commit) ---
    if file_content is not None:
        if not saved_asset_instance:
             card_service_log.error(f"Service: DB commit succeeded but saved_asset_instance is None for {card_id}_{version}. Cannot write file.")
             raise CardServiceError("Failed to get asset instance after DB commit, cannot write file.")

        file_path = _get_file_asset_path(saved_asset_instance)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            card_service_log.info(f"Service: Wrote file content to {file_path}")
        except Exception as e:
            card_service_log.error(f"Service: Failed to write file asset content to {file_path} (DB record committed): {e}")
            raise FileOperationError(f"Asset record created (id={saved_asset_instance.id}), but failed to write file content to {file_path}: {e}")

    if not saved_asset_instance:
         card_service_log.error(f"Service: Reached end of add_file_asset for {card_id}_{version} but saved_asset_instance is invalid.")
         raise CardServiceError("Failed to finalize file asset addition.")

    card_service_log.info(f"Service: File asset addition process completed: id={saved_asset_instance.id}")
    return _map_file_asset_model_to_dto(saved_asset_instance)


def get_context_asset(asset_id: str) -> CardContextAssetDTO:
    """Retrieves a specific context asset by its ID."""
    card_service_log.debug(f"Service: Getting context asset id={asset_id}")
    asset = CardDAO.get_context_asset_by_id(asset_id)
    if not asset:
        raise AssetNotFoundError(f"Context asset with ID {asset_id} not found.")
    return _map_context_asset_model_to_dto(asset)

def get_file_asset(asset_id: str) -> CardFileAssetDTO:
    """Retrieves a specific file asset by its ID."""
    card_service_log.debug(f"Service: Getting file asset id={asset_id}")
    asset = CardDAO.get_file_asset_by_id(asset_id)
    if not asset:
        raise AssetNotFoundError(f"File asset with ID {asset_id} not found.")
    return _map_file_asset_model_to_dto(asset)

def get_file_asset_content(asset_id: str) -> bytes:
    """Retrieves the raw content of a file asset."""
    card_service_log.debug(f"Service: Getting content for file asset id={asset_id}")
    asset = CardDAO.get_file_asset_by_id(asset_id)
    if not asset:
        raise AssetNotFoundError(f"File asset with ID {asset_id} not found.")

    file_path = _get_file_asset_path(asset)
    if not os.path.exists(file_path):
        card_service_log.error(f"Service: File not found for asset {asset_id} at path: {file_path}")
        raise FileNotFoundError(f"File not found at path: {file_path}")

    try:
        with open(file_path, 'rb') as file:
            return file.read()
    except Exception as e:
        card_service_log.error(f"Service: Failed to read file content for asset {asset_id} from {file_path}: {e}")
        raise FileOperationError(f"Failed to read file content from {file_path}: {e}")

def update_context_asset(asset_id: str, update_data: CardAssetCreateUpdateDTO) -> CardContextAssetDTO:
    """Updates an existing context asset."""
    card_service_log.info(f"Service: Updating context asset id={asset_id}")
    updated_asset_instance = None
    card_instance = None
    try:
        asset = CardDAO.get_context_asset_by_id(asset_id)
        if not asset:
            raise AssetNotFoundError(f"Context asset with ID {asset_id} not found.")
        if update_data.data is None:
             raise ValueError("Missing 'data' field for context asset update.")

        asset.type = update_data.type
        asset.tag = update_data.tag
        asset.name = update_data.name
        asset.ext = update_data.ext
        asset.data = update_data.data

        updated_asset_instance = asset

        card = CardDAO.get_card_by_primary_key(asset.card_id, asset.card_version)
        if card:
            card_instance = CardDAO.update_card(card)
        else:
            card_service_log.warning(f"Service: Parent card {asset.card_id}_{asset.card_version} not found while updating asset {asset_id}. Mod time not updated.")
            card_instance = None

        db.session.commit()
        card_service_log.info(f"Service: Context asset updated: id={updated_asset_instance.id}")

        db.session.refresh(updated_asset_instance)
        if card_instance:
            db.session.refresh(card_instance)

        return _map_context_asset_model_to_dto(updated_asset_instance)

    except (SQLAlchemyError, AssetNotFoundError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error updating context asset {asset_id}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error updating context asset {asset_id}: {e}")
        raise CardServiceError(f"An unexpected error occurred while updating the context asset: {e}")

def update_file_asset(asset_id: str, update_data: CardAssetCreateUpdateDTO, new_content: Optional[bytes] = None) -> CardFileAssetDTO:
    """
    Updates an existing file asset's metadata.
    If new_content is provided, it overwrites the existing file content.
    Does NOT handle changing the URI (requires delete/add).
    """
    card_service_log.info(f"Service: Updating file asset id={asset_id}")
    updated_asset_instance = None
    card_instance = None
    try:
        asset = CardDAO.get_file_asset_by_id(asset_id)
        if not asset:
            raise AssetNotFoundError(f"File asset with ID {asset_id} not found.")
        if update_data.uri and update_data.uri != asset.uri:
             raise ValueError("Changing the URI of a file asset is not supported via update. Delete and re-add.")

        asset.type = update_data.type
        asset.tag = update_data.tag
        asset.name = update_data.name
        asset.ext = update_data.ext

        updated_asset_instance = asset

        card = CardDAO.get_card_by_primary_key(asset.card_id, asset.card_version)
        if card:
            card_instance = CardDAO.update_card(card)
        else:
            card_service_log.warning(f"Service: Parent card {asset.card_id}_{asset.card_version} not found while updating asset {asset_id}. Mod time not updated.")
            card_instance = None

        db.session.commit()
        card_service_log.info(f"Service: File asset metadata updated in DB: id={updated_asset_instance.id}")

        db.session.refresh(updated_asset_instance)
        if card_instance:
            db.session.refresh(card_instance)

    except (SQLAlchemyError, AssetNotFoundError, ValueError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error updating file asset metadata {asset_id}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error updating file asset metadata {asset_id}: {e}")
        raise CardServiceError(f"An unexpected error occurred while updating the file asset metadata: {e}")

    # --- File Write Operation (Post-Commit) ---
    if new_content is not None:
        if not updated_asset_instance:
             card_service_log.error(f"Service: DB commit succeeded but updated_asset_instance is None for {asset_id}. Cannot write file.")
             raise CardServiceError("Failed to get asset instance after DB commit, cannot write file.")

        file_path = _get_file_asset_path(updated_asset_instance)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(new_content)
            card_service_log.info(f"Service: Updated file content for asset {asset_id} at {file_path}")
        except Exception as e:
            card_service_log.error(f"Service: Failed to write updated file content for asset {asset_id} to {file_path} (DB changes committed): {e}")
            raise FileOperationError(f"Metadata updated (id={asset_id}), but failed to write updated file content to {file_path}: {e}")

    if not updated_asset_instance:
         card_service_log.error(f"Service: Reached end of update_file_asset for {asset_id} but updated_asset_instance is invalid.")
         raise CardServiceError("Failed to finalize file asset update.")

    card_service_log.info(f"Service: File asset update process completed: id={updated_asset_instance.id}")
    return _map_file_asset_model_to_dto(updated_asset_instance)


def delete_context_asset(asset_id: str) -> None:
    """Deletes a context asset."""
    card_service_log.info(f"Service: Deleting context asset id={asset_id}")
    try:
        asset = CardDAO.get_context_asset_by_id(asset_id)
        if not asset:
            card_service_log.warning(f"Service: Context asset with ID {asset_id} not found for deletion. Assuming already deleted or invalid ID.")
            return

        card_id = asset.card_id
        version = asset.card_version
        CardDAO.delete_context_asset(asset)

        card = CardDAO.get_card_by_primary_key(card_id, version)
        if card:
            CardDAO.update_card(card)
        else:
             card_service_log.warning(f"Service: Parent card {card_id}_{version} not found when deleting asset {asset_id}. Mod time not updated.")

        db.session.commit()
        card_service_log.info(f"Service: Context asset deleted: id={asset_id}")

    except SQLAlchemyError as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error deleting context asset {asset_id}: {e}")
        raise CardServiceError(f"Database error occurred while deleting context asset {asset_id}: {e}")
    except AssetNotFoundError as e:
         card_service_log.error(f"Service: Asset not found error during deletion: {e}")
         raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error deleting context asset {asset_id}: {e}")
        raise CardServiceError(f"An unexpected error occurred while deleting the context asset: {e}")

def delete_file_asset(asset_id: str) -> None:
    """Deletes a file asset record and its corresponding physical file."""
    card_service_log.info(f"Service: Deleting file asset id={asset_id}")
    asset_found = False
    card_id = None
    version = None
    file_path = None
    try:
        asset = CardDAO.get_file_asset_by_id(asset_id)
        if not asset:
            card_service_log.warning(f"Service: File asset with ID {asset_id} not found for deletion. Assuming already deleted or invalid ID.")
            return
        asset_found = True
        card_id = asset.card_id
        version = asset.card_version
        file_path = _get_file_asset_path(asset)

        CardDAO.delete_file_asset(asset)
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if card:
            CardDAO.update_card(card)
        else:
            card_service_log.warning(f"Service: Parent card {card_id}_{version} not found when deleting asset {asset_id}. Mod time not updated.")

        db.session.commit()
        card_service_log.info(f"Service: File asset record deleted from DB: id={asset_id}")

    except SQLAlchemyError as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error deleting file asset record {asset_id} from DB: {e}")
        raise CardServiceError(f"Database error occurred while deleting file asset record {asset_id}: {e}")
    except AssetNotFoundError as e:
         card_service_log.error(f"Service: Asset not found error during DB deletion: {e}")
         raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error deleting file asset record {asset_id} from DB: {e}")
        raise CardServiceError(f"An unexpected error occurred during DB deletion for file asset: {e}")

    # --- Physical File Deletion (Post-Commit) ---
    if asset_found and file_path:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                card_service_log.info(f"Service: Deleted physical file: {file_path}")
                current_dir = os.path.dirname(file_path)
                if card_id and version:
                    card_version_folder = _get_card_asset_folder(card_id, version)
                    while current_dir.startswith(card_version_folder) and current_dir != card_version_folder:
                        try:
                            if not os.listdir(current_dir):
                                os.rmdir(current_dir)
                                card_service_log.debug(f"Service: Removed empty directory: {current_dir}")
                                current_dir = os.path.dirname(current_dir)
                            else:
                                break
                        except OSError as oe:
                             card_service_log.warning(f"Service: Could not remove directory {current_dir}: {oe}")
                             break
                else:
                     card_service_log.warning("Service: card_id or version missing, cannot perform directory cleanup.")


            except Exception as e:
                card_service_log.error(f"Service: Failed to delete physical file {file_path} (DB record committed): {e}")
                raise FileOperationError(f"DB record deleted (id={asset_id}), but failed to delete file at {file_path}: {e}")
        else:
            card_service_log.warning(f"Service: Physical file not found for deleted asset {asset_id} at path: {file_path} (DB record committed)")

    card_service_log.info(f"Service: File asset deletion process completed for id={asset_id}")


def get_card_avatar_url(card_id: str, version: str) -> str:
    """Gets the URL for a card's avatar, or the default if none exists."""
    card_service_log.debug(f"Service: Getting avatar URL for card={card_id}_{version}")
    avatar_asset = CardDAO.get_file_asset_by_tag(card_id, version, 'card_avatar')
    if avatar_asset:
        return _get_file_asset_url(avatar_asset)
    else:
        return _get_default_avatar_url()

def change_card_avatar(card_id: str, version: str, asset_data: CardAssetCreateUpdateDTO, file_content: bytes) -> CardFileAssetDTO:
    """
    Changes the card's avatar. Deletes the old avatar asset (if any)
    and adds a new one with the tag 'card_avatar'.
    """
    card_service_log.info(f"Service: Changing avatar for card={card_id}_{version}")
    if asset_data.tag != 'card_avatar':
        raise ValueError("The tag for the avatar must be 'card_avatar'.")
    if not asset_data.uri:
         raise ValueError("Missing 'uri' field for avatar file asset.")

    # Note: This operation is not fully atomic due to internal commits in delete_file_asset and add_file_asset.
    # A failure after deleting the old avatar but before adding the new one will leave the card without an avatar.
    # For full atomicity, delete/add functions would need refactoring to accept external session/commit control.

    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            raise CardNotFoundError(f"Card {card_id}_{version} not found.")

        existing_avatar = CardDAO.get_file_asset_by_tag(card_id, version, 'card_avatar')
        if existing_avatar:
            try:
                delete_file_asset(existing_avatar.id)
                card_service_log.info(f"Service: Deleted existing avatar asset: id={existing_avatar.id}")
            except (AssetNotFoundError, FileOperationError, CardServiceError) as e:
                 card_service_log.warning(f"Service: Could not fully delete existing avatar asset {existing_avatar.id} during change: {e}")

        new_avatar_dto = add_file_asset(card_id, version, asset_data, file_content)
        card_service_log.info(f"Service: New avatar set for card={card_id}_{version}, asset_id={new_avatar_dto.id}")
        return new_avatar_dto

    except (CardNotFoundError, ValueError, FileOperationError, CardServiceError) as e:
        card_service_log.error(f"Service: Failed to change avatar for card {card_id}_{version}: {e}")
        raise
    except Exception as e:
        card_service_log.error(f"Service: Unexpected error changing avatar for card {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while changing the card avatar: {e}")

# --- Agent Association Service Functions ---

def attach_agent_to_card(card_id: str, version: str, agent_id: str) -> bool:
    """Attaches an agent to a specific card version."""
    card_service_log.info(f"Service: Attaching agent {agent_id} to card {card_id}_{version}")
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            raise CardNotFoundError(f"Card {card_id}_{version} not found.")

        attached = CardDAO.attach_agent_to_card(card, agent_id)

        if attached:
            CardDAO.update_card(card)
            db.session.commit()
            card_service_log.info(f"Service: Agent {agent_id} attached successfully to card {card_id}_{version}.")
            return True
        else:
            card_service_log.warning(f"Service: Agent {agent_id} could not be attached to card {card_id}_{version} (agent not found or already attached).")
            return False

    except (SQLAlchemyError, CardNotFoundError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error attaching agent {agent_id} to card {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error attaching agent {agent_id} to card {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while attaching the agent: {e}")


def detach_agent_from_card(card_id: str, version: str, agent_id: str) -> bool:
    """Detaches an agent from a specific card version."""
    card_service_log.info(f"Service: Detaching agent {agent_id} from card {card_id}_{version}")
    try:
        card = CardDAO.get_card_by_primary_key(card_id, version)
        if not card:
            raise CardNotFoundError(f"Card {card_id}_{version} not found.")

        detached = CardDAO.detach_agent_from_card(card, agent_id)

        if detached:
            CardDAO.update_card(card)
            db.session.commit()
            card_service_log.info(f"Service: Agent {agent_id} detached successfully from card {card_id}_{version}.")
            return True
        else:
            card_service_log.warning(f"Service: Agent {agent_id} could not be detached from card {card_id}_{version} (agent not found or not attached).")
            return False

    except (SQLAlchemyError, CardNotFoundError) as e:
        db.session.rollback()
        card_service_log.error(f"Service: Error detaching agent {agent_id} from card {card_id}_{version}: {e}")
        raise
    except Exception as e:
        db.session.rollback()
        card_service_log.error(f"Service: Unexpected error detaching agent {agent_id} from card {card_id}_{version}: {e}")
        raise CardServiceError(f"An unexpected error occurred while detaching the agent: {e}")