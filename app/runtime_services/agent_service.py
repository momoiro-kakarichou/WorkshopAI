from typing import Dict, Any, List, Optional
from app.extensions import db
from app.dao.agent_dao import AgentDAO
from app.dto.agent_dto import (
    AgentCoreDTO, AgentListDTO, AgentDetailDTO, AgentRuntimeInfoDTO,
    AgentFullDTO, AgentCreateDTO, AgentUpdateDTO
)
from app.runtime.agent_runtime import AgentRuntime
from app.dao.workflow_dao import WorkflowDAO
from app.models.utils import MessageBroker
from app.utils.utils import create_logger
from app.scheduler import CyclicTaskManager
from app.context import context

agent_service_log = create_logger(__name__, entity_name='AGENT_SERVICE', level=context.log_level)

class AgentService:
    """Service layer for managing Agents, their persistence, and runtime state."""

    def __init__(self):
        self.broker: MessageBroker = None
        self.cyclic_task_manager: CyclicTaskManager = context.cyclic_task_manager
        self.active_runtimes: Dict[str, AgentRuntime] = {}
        agent_service_log.info("AgentService initialized.")
    
    def init_app(self, app, broker):
        self.app_instance = app
        self.broker = broker

    def get_agent_full_info(self, agent_id: str) -> Optional[AgentFullDTO]:
        """Retrieves detailed information about an agent, including runtime status."""
        agent = AgentDAO.get_agent_by_id(agent_id)
        if not agent:
            return None

        versions = AgentDAO.get_agent_versions(agent.name)
        agent_vars = {var.name: var.value for var in agent.variables}

        detail_dto = AgentDetailDTO(
            id=agent.id,
            name=agent.name,
            version=agent.version,
            description=agent.description,
            workflow_id=agent.workflow_id,
            vars=agent_vars,
            versions_list=versions
        )

        runtime_info = AgentRuntimeInfoDTO(is_started=False)
        if agent_id in self.active_runtimes:
            runtime_instance = self.active_runtimes[agent_id]
            runtime_info.is_started = runtime_instance.is_started

        full_dto = AgentFullDTO(**detail_dto.__dict__, **runtime_info.__dict__)
        return full_dto

    def get_agent_list(self) -> List[AgentListDTO]:
        """Retrieves a list of all agents (ID and name)."""
        agent_ids = AgentDAO.get_agent_list_ids()
        agent_list = []
        for agent_id in agent_ids:
            agent = AgentDAO.get_agent_by_id(agent_id)
            if agent:
                agent_list.append(AgentListDTO(id=agent.id, name=agent.name))
        # TODO: Optimize this query in AgentDAO
        return agent_list

    def create_agent(self, create_dto: AgentCreateDTO) -> AgentCoreDTO:
        """Creates a new agent."""
        agent = None
        try:
            agent_data = {
                "name": create_dto.name,
                "workflow_id": create_dto.workflow_id,
                "description": create_dto.description or '',
                "version": create_dto.version or '1.0.0'
            }
            agent = AgentDAO.create_agent(agent_data, session=db.session)
            db.session.flush()

            if create_dto.vars:
                AgentDAO.update_agent_variables(agent, create_dto.vars, session=db.session)

            db.session.commit()
            agent_service_log.info(f"Agent {agent.id} created successfully.")

            final_agent = AgentDAO.get_agent_by_id(agent.id, session=db.session)
            return AgentCoreDTO(
                id=final_agent.id,
                name=final_agent.name,
                version=final_agent.version,
                description=final_agent.description,
                workflow_id=final_agent.workflow_id,
                vars={var.name: var.value for var in final_agent.variables}
            )
        except Exception as e:
            db.session.rollback()
            agent_id_str = f" (attempted ID: {agent.id})" if agent and agent.id else ""
            agent_service_log.exception(f"Error creating agent{agent_id_str}: {e}")
            raise


    def update_agent(self, agent_id: str, update_dto: AgentUpdateDTO) -> bool:
        """Updates an existing agent's persistent data."""
        agent = AgentDAO.get_agent_by_id(agent_id, session=db.session)
        if not agent:
            agent_service_log.error(f"Update failed: Agent {agent_id} not found.")
            return False

        update_data = update_dto.__dict__
        update_data = {k: v for k, v in update_data.items() if v is not None and k != 'vars'}

        try:
            if update_data:
                AgentDAO.update_agent_from_dict(agent, update_data, session=db.session)

            if update_dto.vars is not None:
                AgentDAO.update_agent_variables(agent, update_dto.vars, session=db.session)
                if agent_id in self.active_runtimes:
                    self.active_runtimes[agent_id].update_vars(update_dto.vars)

            db.session.commit()
            agent_service_log.info(f"Agent {agent_id} updated successfully.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error updating agent {agent_id}: {e}")
            db.session.rollback()
            return False


    def delete_agent(self, agent_id: str) -> bool:
        """Deletes an agent after stopping it if running."""
        agent = AgentDAO.get_agent_by_id(agent_id, session=db.session)
        if not agent:
            agent_service_log.warning(f"Deletion failed: Agent {agent_id} not found.")
            return False

        if agent_id in self.active_runtimes:
            agent_service_log.info(f"Agent {agent_id} is running. Stopping before deletion.")
            stop_success = self.stop_agent(agent_id)
            if not stop_success:
                agent_service_log.error(f"Failed to stop agent {agent_id} before deletion. Aborting delete.")
                return False

        try:
            AgentDAO.delete_agent(agent, session=db.session)
            db.session.commit()
            agent_service_log.info(f"Agent {agent_id} deleted successfully.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error deleting agent {agent_id} from database: {e}")
            db.session.rollback()
            return False


    def start_agent(self, agent_id: str) -> bool:
        """Starts the runtime for a specific agent."""
        if agent_id in self.active_runtimes and self.active_runtimes[agent_id].is_started:
            agent_service_log.warning(f"Agent {agent_id} is already started.")
            return True

        agent = AgentDAO.get_agent_by_id(agent_id)
        if not agent:
            agent_service_log.error(f"Start failed: Agent {agent_id} not found.")
            return False

        workflow_dao = WorkflowDAO()
        workflow_exists = workflow_dao.get_workflow_by_id(agent.workflow_id, load_relations=False) is not None
        if not workflow_exists:
            agent_service_log.error(f"Start failed: Workflow {agent.workflow_id} for agent {agent_id} not found.")
            return False

        try:
            initial_vars = {var.name: var.value for var in agent.variables}
            runtime_instance = AgentRuntime(
                agent_id=agent.id,
                agent_name=agent.name,
                workflow_id=agent.workflow_id,
                initial_vars=initial_vars,
                app_instance=self.app_instance
            )
            runtime_instance.start(self.broker, self.cyclic_task_manager)

            self.active_runtimes[agent_id] = runtime_instance
            agent_service_log.info(f"Agent {agent_id} started successfully.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error starting agent {agent_id}: {e}")
            if agent_id in self.active_runtimes:
                 del self.active_runtimes[agent_id]
            return False


    def stop_agent(self, agent_id: str) -> bool:
        """Stops the runtime for a specific agent."""
        if agent_id not in self.active_runtimes:
            agent_service_log.warning(f"Stop failed: Agent {agent_id} is not currently running.")
            return False

        runtime_instance = self.active_runtimes[agent_id]
        try:
            runtime_instance.stop()
            del self.active_runtimes[agent_id]
            agent_service_log.info(f"Agent {agent_id} stopped successfully.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error stopping agent {agent_id}: {e}")
            return False


    def add_agent_variable(self, agent_id: str, var_name: str, var_type: str) -> bool:
        """Adds a new variable to an agent."""
        agent = AgentDAO.get_agent_by_id(agent_id, session=db.session)
        if not agent:
            agent_service_log.error(f"Add variable failed: Agent {agent_id} not found.")
            return False

        if any(v.name == var_name for v in agent.variables):
             agent_service_log.warning(f"Add variable failed: Variable '{var_name}' already exists for agent {agent_id}.")
             return False

        if var_type == 'text':
            value = ''
        elif var_type == 'array':
            value = []
        else:
            value = None
            agent_service_log.warning(f"Adding variable '{var_name}' for agent {agent_id} with unknown type '{var_type}'. Defaulting value to None.")

        try:
            AgentDAO.add_variable_to_agent(agent, var_name, value, session=db.session)
            db.session.commit()

            if agent_id in self.active_runtimes:
                self.active_runtimes[agent_id].vars[var_name] = value
                agent_service_log.info(f"Runtime variables updated for running agent {agent_id} after adding variable '{var_name}'.")

            agent_service_log.info(f"Variable '{var_name}' added to agent {agent_id}.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error adding variable '{var_name}' to agent {agent_id}: {e}")
            db.session.rollback() # Rollback on error
            return False


    def import_agent_variables(self, agent_id: str, variables_data: Dict[str, Any]) -> bool:
        """Imports variables, replacing existing ones for the agent."""
        agent = AgentDAO.get_agent_by_id(agent_id, session=db.session)
        if not agent:
            agent_service_log.error(f"Import variables failed: Agent {agent_id} not found.")
            return False

        if not isinstance(variables_data, dict):
            agent_service_log.error(f"Import variables failed for agent {agent_id}: Invalid format. Expected a dictionary.")
            return False

        try:
            AgentDAO.update_agent_variables(agent, variables_data, session=db.session)
            db.session.commit()

            if agent_id in self.active_runtimes:
                self.active_runtimes[agent_id].update_vars(variables_data)
                agent_service_log.info(f"Runtime variables updated for running agent {agent_id} after import.")

            agent_service_log.info(f"Variables imported successfully for agent {agent_id}.")
            return True
        except Exception as e:
            agent_service_log.exception(f"Error importing variables for agent {agent_id}: {e}")
            db.session.rollback()
            return False


    def delete_agent_variable(self, agent_id: str, var_name: str) -> bool:
        """Deletes a specific variable from an agent."""
        agent = AgentDAO.get_agent_by_id(agent_id, session=db.session)
        if not agent:
            agent_service_log.error(f"Delete variable failed: Agent {agent_id} not found.")
            return False

        try:
            deleted = AgentDAO.delete_variable_from_agent(agent, var_name, session=db.session)
            if deleted:
                db.session.commit() # Commit transaction

                if agent_id in self.active_runtimes:
                    if var_name in self.active_runtimes[agent_id].vars:
                        del self.active_runtimes[agent_id].vars[var_name]
                        agent_service_log.info(f"Runtime variable '{var_name}' removed for running agent {agent_id}.")
                    else:
                        agent_service_log.warning(f"Runtime variable '{var_name}' not found for running agent {agent_id} during delete.")


                agent_service_log.info(f"Variable '{var_name}' deleted from agent {agent_id}.")
                return True
            else:
                agent_service_log.warning(f"Delete variable failed: Variable '{var_name}' not found for agent {agent_id}.")
                return False
        except Exception as e:
            agent_service_log.exception(f"Error deleting variable '{var_name}' from agent {agent_id}: {e}")
            db.session.rollback()
            return False