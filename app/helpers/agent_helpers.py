from sqlalchemy.orm.exc import NoResultFound
from typing import Any
from app.models.agent_variable import AgentVariable
from app.utils.db import add_changes, commit_changes
from app.extensions import log

def update_agent_variable(agent_id: str, variable_name: str, new_value: Any):
    """
    Updates the value of a specific variable for a given agent in the database.

    Args:
        agent_id: The ID of the agent whose variable needs updating.
        variable_name: The name of the variable to update.
        new_value: The new value for the variable.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    try:
        variable = AgentVariable.query.filter_by(agent_id=agent_id, name=variable_name).one()

        variable.value = new_value

        add_changes(variable)
        commit_changes()
        log.debug(f"Agent {agent_id}: Variable '{variable_name}' updated successfully.")
        return True
    except NoResultFound:
        log.error(f"Agent {agent_id}: Variable '{variable_name}' not found for update.")
        return False
    except Exception as e:
        log.error(f"Agent {agent_id}: Error updating variable '{variable_name}': {e}")
        return False