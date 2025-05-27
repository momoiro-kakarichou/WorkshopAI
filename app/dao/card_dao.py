from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, delete as sqlalchemy_delete, func
from sqlalchemy.orm import Session, selectinload, attributes

from app.extensions import db
from app.models.card import Card, CardContextAsset, CardFileAsset
from app.utils.utils import create_logger
from app.context import context

card_dao_log = create_logger(__name__, entity_name='CARD_DAO', level=context.log_level)

class CardDAO:
    """Data Access Object for Card and related Asset operations."""

    @staticmethod
    def _get_session(session: Optional[Session] = None) -> Session:
        """Gets the current session or the default one."""
        return session or db.session

    @staticmethod
    def get_card_by_primary_key(id: str, version: str, session: Optional[Session] = None) -> Optional[Card]:
        """Retrieves a card by its composite primary key (id and version)."""
        card_dao_log.debug(f"DAO: Fetching card by PK: id={id}, version={version}")
        current_session = CardDAO._get_session(session)
        return current_session.get(Card, (id, version))

    @staticmethod
    def get_cards_by_id(id: str, session: Optional[Session] = None) -> List[Card]:
        """Retrieves all versions of a card by its ID, ordered by creation date."""
        card_dao_log.debug(f"DAO: Fetching all cards by id={id}")
        current_session = CardDAO._get_session(session)
        stmt = select(Card).where(Card.id == id).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        ).order_by(Card.creation_date)
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def get_latest_card_by_id(id: str, session: Optional[Session] = None) -> Optional[Card]:
        """Retrieves the latest version of a card by its ID."""
        card_dao_log.debug(f"DAO: Fetching latest card by id={id}")
        current_session = CardDAO._get_session(session)
        # Order by creation_date descending and take the first one
        stmt = select(Card).where(Card.id == id).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        ).order_by(Card.creation_date.desc()).limit(1)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_distinct_card_ids(session: Optional[Session] = None) -> List[str]:
        """Retrieves a list of all unique card IDs."""
        card_dao_log.debug("DAO: Fetching all distinct card IDs")
        current_session = CardDAO._get_session(session)
        stmt = select(Card.id).distinct()
        return [card_id for card_id, in current_session.execute(stmt).all()]

    @staticmethod
    def get_all_cards(session: Optional[Session] = None) -> List[Card]:
        """Retrieves all card entities from the database."""
        card_dao_log.debug("DAO: Fetching all cards")
        current_session = CardDAO._get_session(session)
        stmt = select(Card).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def get_cards_by_chat_id(chat_id: str, session: Optional[Session] = None) -> List[Card]:
        """Retrieves all cards associated with a given chat ID."""
        card_dao_log.debug(f"DAO: Fetching cards by chat_id={chat_id}")
        current_session = CardDAO._get_session(session)
        from app.models.card import card_chat_association
        stmt = select(Card).join(card_chat_association).where(
            card_chat_association.c.chat_id == chat_id
        ).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def get_cards_by_name(name: str, session: Optional[Session] = None) -> List[Card]:
        """Retrieves all cards matching the given name exactly."""
        card_dao_log.debug(f"DAO: Fetching cards by name='{name}'")
        current_session = CardDAO._get_session(session)
        stmt = select(Card).where(Card.name == name).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def filter_cards_by_name_part(name_part: str, session: Optional[Session] = None) -> List[Card]:
        """Retrieves cards where the name contains the given substring (case-insensitive)."""
        if not name_part:
            card_dao_log.warning("DAO: filter_cards_by_name_part called with empty name_part.")
            return []
        card_dao_log.debug(f"DAO: Filtering cards by name part: '%{name_part}%'")
        current_session = CardDAO._get_session(session)
        stmt = select(Card).where(Card.name.ilike(f"%{name_part}%")).options(
            selectinload(Card.context_assets),
            selectinload(Card.file_assets),
            selectinload(Card.agents),
            selectinload(Card.chats)
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def save_card(card: Card, session: Optional[Session] = None) -> Card:
        """Adds a Card instance to the session (no commit)."""
        card_dao_log.debug(f"DAO: Adding card id={card.id}, version={card.version} to session")
        current_session = CardDAO._get_session(session)
        current_session.add(card)
        return card

    @staticmethod
    def update_card(card: Card, session: Optional[Session] = None) -> Card:
        """Marks a card as modified (no commit)."""
        card_dao_log.debug(f"DAO: Marking card id={card.id}, version={card.version} as modified")
        current_session = CardDAO._get_session(session)
        if card not in current_session:
             current_session.merge(card)

        card.modification_date = datetime.now(timezone.utc)
        return card

    @staticmethod
    def delete_card(card: Card, session: Optional[Session] = None) -> None:
        """Marks a specific Card instance for deletion (no commit)."""
        card_dao_log.debug(f"DAO: Marking card id={card.id}, version={card.version} for deletion")
        current_session = CardDAO._get_session(session)
        current_session.delete(card)

    @staticmethod
    def delete_cards_by_id(id: str, session: Optional[Session] = None) -> int:
        """Marks all versions of a card for deletion by its ID (no commit)."""
        card_dao_log.debug(f"DAO: Marking all cards with id={id} for deletion")
        current_session = CardDAO._get_session(session)
        stmt_select = select(Card).where(Card.id == id)
        cards_to_delete = current_session.execute(stmt_select).scalars().all()
        count = len(cards_to_delete)

        if count == 0:
            card_dao_log.warning(f"DAO: No cards found with ID {id} to delete.")
            return 0

        stmt_delete = sqlalchemy_delete(Card).where(Card.id == id)
        current_session.execute(stmt_delete)
        card_dao_log.info(f"DAO: Marked {count} versions of card {id} for deletion.")
        return count

    # --- Card Context Asset DAO Methods ---

    @staticmethod
    def get_context_asset_by_id(asset_id: str, session: Optional[Session] = None) -> Optional[CardContextAsset]:
        """Retrieves a CardContextAsset by its ID."""
        card_dao_log.debug(f"DAO: Fetching context asset by id={asset_id}")
        current_session = CardDAO._get_session(session)
        return current_session.get(CardContextAsset, asset_id)

    @staticmethod
    def get_context_assets_by_card(card_id: str, card_version: str, session: Optional[Session] = None) -> List[CardContextAsset]:
        """Retrieves all context assets for a specific card version."""
        card_dao_log.debug(f"DAO: Fetching context assets for card={card_id}_{card_version}")
        current_session = CardDAO._get_session(session)
        stmt = select(CardContextAsset).where(
            CardContextAsset.card_id == card_id,
            CardContextAsset.card_version == card_version
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def save_context_asset(asset: CardContextAsset, session: Optional[Session] = None) -> CardContextAsset:
        """Adds a CardContextAsset instance to the session (no commit)."""
        card_dao_log.debug(f"DAO: Adding context asset id={asset.id} for card={asset.card_id}_{asset.card_version}")
        current_session = CardDAO._get_session(session)
        current_session.add(asset)
        return asset

    @staticmethod
    def delete_context_asset(asset: CardContextAsset, session: Optional[Session] = None) -> None:
        """Marks a CardContextAsset instance for deletion (no commit)."""
        card_dao_log.debug(f"DAO: Marking context asset id={asset.id} for deletion")
        current_session = CardDAO._get_session(session)
        current_session.delete(asset)

    @staticmethod
    def delete_context_assets_by_card_id(card_id: str, session: Optional[Session] = None) -> int:
        """Marks all context assets associated with a card ID for deletion (no commit)."""
        card_dao_log.debug(f"DAO: Marking all context assets for card_id={card_id} for deletion")
        current_session = CardDAO._get_session(session)
        stmt_count = select(func.count(CardContextAsset.id)).where(CardContextAsset.card_id == card_id)
        count = current_session.execute(stmt_count).scalar_one()

        if count == 0:
            card_dao_log.debug(f"DAO: No context assets found for card ID {card_id} to delete.")
            return 0

        stmt_delete = sqlalchemy_delete(CardContextAsset).where(CardContextAsset.card_id == card_id)
        current_session.execute(stmt_delete)
        card_dao_log.info(f"DAO: Marked {count} context assets for card {card_id} for deletion.")
        return count


    # --- Card File Asset DAO Methods ---

    @staticmethod
    def get_file_asset_by_id(asset_id: str, session: Optional[Session] = None) -> Optional[CardFileAsset]:
        """Retrieves a CardFileAsset by its ID."""
        card_dao_log.debug(f"DAO: Fetching file asset by id={asset_id}")
        current_session = CardDAO._get_session(session)
        return current_session.get(CardFileAsset, asset_id)

    @staticmethod
    def get_file_assets_by_card(card_id: str, card_version: str, session: Optional[Session] = None) -> List[CardFileAsset]:
        """Retrieves all file assets for a specific card version."""
        card_dao_log.debug(f"DAO: Fetching file assets for card={card_id}_{card_version}")
        current_session = CardDAO._get_session(session)
        stmt = select(CardFileAsset).where(
            CardFileAsset.card_id == card_id,
            CardFileAsset.card_version == card_version
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def get_file_asset_by_tag(card_id: str, card_version: str, tag: str, session: Optional[Session] = None) -> Optional[CardFileAsset]:
        """Retrieves a file asset by card and tag."""
        card_dao_log.debug(f"DAO: Fetching file asset for card={card_id}_{card_version} with tag='{tag}'")
        current_session = CardDAO._get_session(session)
        stmt = select(CardFileAsset).where(
            CardFileAsset.card_id == card_id,
            CardFileAsset.card_version == card_version,
            CardFileAsset.tag == tag
        )
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def save_file_asset(asset: CardFileAsset, session: Optional[Session] = None) -> CardFileAsset:
        """Adds a CardFileAsset instance to the session (no commit)."""
        card_dao_log.debug(f"DAO: Adding file asset id={asset.id} for card={asset.card_id}_{asset.card_version}")
        current_session = CardDAO._get_session(session)
        current_session.add(asset)
        return asset

    @staticmethod
    def delete_file_asset(asset: CardFileAsset, session: Optional[Session] = None) -> None:
        """Marks a CardFileAsset instance for deletion (no commit)."""
        card_dao_log.debug(f"DAO: Marking file asset id={asset.id} for deletion")
        current_session = CardDAO._get_session(session)
        current_session.delete(asset)

    @staticmethod
    def delete_file_assets_by_card_id(card_id: str, session: Optional[Session] = None) -> int:
        """Marks all file assets associated with a card ID for deletion (no commit)."""
        card_dao_log.debug(f"DAO: Marking all file assets for card_id={card_id} for deletion")
        current_session = CardDAO._get_session(session)
        stmt_count = select(func.count(CardFileAsset.id)).where(CardFileAsset.card_id == card_id)
        count = current_session.execute(stmt_count).scalar_one()

        if count == 0:
            card_dao_log.debug(f"DAO: No file assets found for card ID {card_id} to delete.")
            return 0

        stmt_delete = sqlalchemy_delete(CardFileAsset).where(CardFileAsset.card_id == card_id)
        current_session.execute(stmt_delete)
        card_dao_log.info(f"DAO: Marked {count} file asset records for card {card_id} for deletion.")
        return count

    # --- Agent Association ---

    @staticmethod
    def attach_agent_to_card(card: Card, agent_id: str, session: Optional[Session] = None) -> bool:
        """Attaches an agent to a card if not already attached (no commit)."""
        current_session = CardDAO._get_session(session)
        from app.models.agent import Agent
        agent = current_session.get(Agent, agent_id)
        if not agent:
            card_dao_log.error(f"DAO: Agent with ID {agent_id} not found for attaching to card {card.id}.")
            return False

        if card not in current_session:
            card = current_session.merge(card)

        if agent not in card.agents:
            card.agents.append(agent)
            card_dao_log.debug(f"DAO: Attached agent {agent_id} to card {card.id}_{card.version}")
            return True
        card_dao_log.debug(f"DAO: Agent {agent_id} already attached to card {card.id}_{card.version}")
        return False

    @staticmethod
    def detach_agent_from_card(card: Card, agent_id: str, session: Optional[Session] = None) -> bool:
        """Detaches an agent from a card if attached (no commit)."""
        current_session = CardDAO._get_session(session)
        if card not in current_session:
            card = current_session.merge(card)
        if not attributes.instance_state(card).has_identity or 'agents' not in attributes.instance_state(card).committed_state:
             current_session.refresh(card, ['agents'])


        agent_to_detach = next((a for a in card.agents if a.id == agent_id), None)

        if agent_to_detach:
            card.agents.remove(agent_to_detach)
            card_dao_log.debug(f"DAO: Detached agent {agent_id} from card {card.id}_{card.version}")
            return True

        card_dao_log.warning(f"DAO: Agent {agent_id} not found attached to card {card.id}_{card.version} for detaching.")
        return False