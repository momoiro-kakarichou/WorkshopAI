from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.extensions import db
from app.models.agent import Agent
from app.models.agent_variable import AgentVariable

class AgentDAO:
    """Data Access Object for Agent operations."""

    @staticmethod
    def get_agent_by_id(agent_id: str, session: Optional[Session] = None) -> Optional[Agent]:
        """Fetches an agent by its ID, eagerly loading variables."""
        current_session = session or db.session
        stmt = select(Agent).options(selectinload(Agent.variables)).where(Agent.id == agent_id)
        return current_session.execute(stmt).scalar_one_or_none()


    @staticmethod
    def get_agent_list_ids(session: Optional[Session] = None) -> List[str]:
        """Fetches a list of all agent IDs."""
        current_session = session or db.session
        stmt = select(Agent.id)
        return [agent_id for agent_id, in current_session.execute(stmt).all()]

    @staticmethod
    def get_agent_versions(agent_name: str, session: Optional[Session] = None) -> List[str]:
        """Fetches distinct versions for a given agent name."""
        current_session = session or db.session
        stmt = select(Agent.version).where(Agent.name == agent_name).distinct()
        return [v for v, in current_session.execute(stmt).all()]

    @staticmethod
    def create_agent(agent_data: Dict[str, Any], session: Optional[Session] = None) -> Agent:
        """Creates a new agent instance and adds it to the session (no commit)."""
        agent = Agent(**agent_data)
        current_session = session or db.session
        current_session.add(agent)
        return agent

    @staticmethod
    def update_agent_from_dict(agent: Agent, data: Dict[str, Any], session: Optional[Session] = None):
        """Updates an agent instance from a dictionary (no commit)."""
        for key, value in data.items():
            if key in ['id', 'variables'] or not hasattr(agent, key):
                continue
            setattr(agent, key, value)

    @staticmethod
    def delete_agent(agent: Agent, session: Optional[Session] = None):
        """Marks an agent instance for deletion (no commit)."""
        current_session = session or db.session
        current_session.delete(agent)

    @staticmethod
    def add_variable_to_agent(agent: Agent, var_name: str, var_value: Any, session: Optional[Session] = None):
        """Adds a new variable to an agent (no commit)."""
        current_session = session or db.session

        new_var = AgentVariable(agent_id=agent.id, name=var_name, value=var_value)
        agent.variables.append(new_var)
        current_session.add(new_var)


    @staticmethod
    def delete_variable_from_agent(agent: Agent, var_name: str, session: Optional[Session] = None) -> bool:
        """Deletes a variable from an agent by name (no commit)."""
        current_session = session or db.session

        variable_to_delete = None
        for var in agent.variables:
            if var.name == var_name:
                variable_to_delete = var
                break

        if variable_to_delete:
            agent.variables.remove(variable_to_delete)
            current_session.delete(variable_to_delete)
            return True
        return False

    @staticmethod
    def update_agent_variables(agent: Agent, variables_data: Dict[str, Any], session: Optional[Session] = None):
        """Replaces agent variables from a dictionary (no commit)."""
        current_session = session or db.session

        existing_vars = list(agent.variables)
        for var in existing_vars:
            current_session.delete(var)
        agent.variables.clear()

        for name, value in variables_data.items():
            new_var = AgentVariable(agent_id=agent.id, name=name, value=value)
            agent.variables.append(new_var)
            current_session.add(new_var)