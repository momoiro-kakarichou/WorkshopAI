from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func
from app.extensions import db
from app.models.api import Api

class ApiDAO:
    """Data Access Object for Api model operations."""

    @staticmethod
    def get_api_by_id(api_id: str, session: Optional[Session] = None) -> Optional[Api]:
        """Fetches an API configuration by its ID."""
        current_session = session or db.session
        stmt = select(Api).where(Api.id == api_id)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_api_list(api_type: str, source: str, session: Optional[Session] = None) -> List[Api]:
        """Fetches a list of API configurations filtered by type and source."""
        current_session = session or db.session
        stmt = select(Api).where(Api.api_type == api_type, Api.source == source)
        return list(current_session.execute(stmt).scalars().all())

    @staticmethod
    def get_api_ids_and_names(api_type: str, source: Optional[str] = None, session: Optional[Session] = None) -> List[Tuple[str, str]]:
        """Fetches a list of (id, name) tuples for APIs filtered by type and optionally by source."""
        current_session = session or db.session
        stmt = select(Api.id, Api.name).where(Api.api_type == api_type)
        if source:
            stmt = stmt.where(Api.source == source)
        return list(current_session.execute(stmt).all())

    @staticmethod
    def create_api(api_data: dict, session: Optional[Session] = None) -> Api:
        """Creates a new Api instance and adds it to the session (no commit)."""
        api = Api(**api_data)
        current_session = session or db.session
        current_session.add(api)
        return api

    @staticmethod
    def update_api_from_dict(api: Api, data: dict, session: Optional[Session] = None):
        """Updates an Api instance from a dictionary (no commit)."""
        for key, value in data.items():
            if key == 'id' or not hasattr(api, key):
                continue
            setattr(api, key, value)

    @staticmethod
    def delete_api(api: Api, session: Optional[Session] = None):
        """Marks an Api instance for deletion (no commit)."""
        current_session = session or db.session
        current_session.delete(api)

    @staticmethod
    def delete_api_by_id(api_id: str, session: Optional[Session] = None) -> int:
        """Deletes an Api instance by ID directly using a delete statement (no commit).
           Returns the number of rows affected.
        """
        current_session = session or db.session
        stmt = delete(Api).where(Api.id == api_id)
        result = current_session.execute(stmt)
        return result.rowcount

    @staticmethod
    def get_apis_by_tag(tag: str, session: Optional[Session] = None) -> List[Api]:
        """Fetches a list of API configurations that include the given tag."""
        current_session = session or db.session
        stmt = select(Api).where(Api.tags.like(f'%"{tag}"%'))
        return list(current_session.execute(stmt).scalars().all())

    @staticmethod
    def get_random_api_by_tag(tag: str, session: Optional[Session] = None) -> Optional[Api]:
        """Fetches a random API configuration that includes the given tag."""
        current_session = session or db.session
        stmt = select(Api).where(Api.tags.like(f'%"{tag}"%')).order_by(func.random()).limit(1)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_distinct_tags(session: Optional[Session] = None) -> List[str]:
        """Fetches all distinct tags from all API configurations."""
        current_session = session or db.session
        stmt = select(Api.tags)
        all_tags_lists = current_session.execute(stmt).scalars().all()

        distinct_tags = set()
        for tags_list in all_tags_lists:
            if isinstance(tags_list, list):  # tags are expected to be a list of strings
                for tag in tags_list:
                    if isinstance(tag, str):  # Ensure individual tags are strings
                        distinct_tags.add(tag)
        return sorted(list(distinct_tags))