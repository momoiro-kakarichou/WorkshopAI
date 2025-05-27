from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete as sqlalchemy_delete
from sqlalchemy.orm import Session, selectinload, attributes
from app.extensions import db
from app.models.workflow import Workflow, Node, Link, WorkflowTempVar
from app.utils.utils import create_logger
from app.context import context

wf_dao_log = create_logger(__name__, entity_name='WORKFLOW_DAO', level=context.log_level)

class WorkflowDAO:
    """Data Access Object for Workflow related operations using static methods."""

    @staticmethod
    def _get_session(session: Optional[Session] = None) -> Session:
        """Gets the provided session or the default one."""
        return session or db.session

    @staticmethod
    def _ensure_attached(entity: Any, session: Session) -> Any:
        """Ensures the entity is attached to the provided session."""
        state = attributes.instance_state(entity)
        if not state.session or state.session is not session:
             return session.merge(entity)
        return entity

    @staticmethod
    def get_workflow_by_id(workflow_id: str, load_relations: bool = True, session: Optional[Session] = None) -> Optional[Workflow]:
        """Retrieves a Workflow by its ID, optionally loading relations."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt = select(Workflow).where(Workflow.id == workflow_id)
            if load_relations:
                stmt = stmt.options(
                    selectinload(Workflow.nodes),
                    selectinload(Workflow.links)
                )
            workflow = current_session.execute(stmt).scalar_one_or_none()
            return workflow
        except Exception as e:
            wf_dao_log.error(f"Error fetching workflow {workflow_id}: {e}")
            raise

    @staticmethod
    def get_workflow_list_ids(session: Optional[Session] = None) -> List[str]:
        """Retrieves a list of all workflow IDs."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt = select(Workflow.id)
            return [wf_id for wf_id, in current_session.execute(stmt).all()]
        except Exception as e:
            wf_dao_log.error(f"Error fetching workflow list IDs: {e}")
            raise

    @staticmethod
    def create_workflow(name: str, graph: Dict[str, Any], session: Optional[Session] = None) -> Workflow:
        """Creates a new workflow instance and adds it to the session (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            workflow = Workflow(name=name, graph=graph)
            current_session.add(workflow)
            wf_dao_log.info(f"Workflow '{name}' added to session (ID pending flush: {workflow.id}).")
            return workflow
        except Exception as e:
            wf_dao_log.error(f"Error creating workflow instance '{name}': {e}")
            raise

    @staticmethod
    def update_workflow(workflow: Workflow, data: Dict[str, Any], session: Optional[Session] = None) -> Workflow:
        """Updates an existing workflow instance with data (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            attached_workflow = WorkflowDAO._ensure_attached(workflow, current_session)
            for key, value in data.items():
                 if hasattr(attached_workflow, key) and key not in ['id', 'nodes', 'links', 'temp_vars']:
                    setattr(attached_workflow, key, value)
            wf_dao_log.info(f"Workflow '{attached_workflow.name}' (ID: {attached_workflow.id}) updated in session.")
            return attached_workflow
        except Exception as e:
            wf_dao_log.error(f"Error updating workflow {workflow.id}: {e}")
            raise

    @staticmethod
    def delete_workflow(workflow: Workflow, session: Optional[Session] = None) -> None:
        """Marks a workflow for deletion (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            workflow_id = workflow.id
            attached_workflow = WorkflowDAO._ensure_attached(workflow, current_session)
            current_session.delete(attached_workflow)
            wf_dao_log.info(f"Workflow ID: {workflow_id} marked for deletion.")
        except Exception as e:
            wf_dao_log.error(f"Error marking workflow {workflow.id} for deletion: {e}")
            raise

    @staticmethod
    def add_node_to_workflow(workflow: Workflow, node_data: Dict[str, Any], session: Optional[Session] = None) -> Node:
        """Adds a new node to a workflow (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            attached_workflow = WorkflowDAO._ensure_attached(workflow, current_session)
            if 'workflow_id' not in node_data:
                 node_data['workflow_id'] = attached_workflow.id
            elif node_data.get('workflow_id') != attached_workflow.id:
                 wf_dao_log.warning(f"Workflow ID mismatch for node '{node_data.get('name', 'N/A')}': node_data has {node_data.get('workflow_id')}, workflow object has {attached_workflow.id}. Using workflow object ID.")
                 node_data['workflow_id'] = attached_workflow.id

            node = Node(**node_data)
            attached_workflow.nodes.append(node)
            current_session.add(node)
            wf_dao_log.info(f"Node '{node.name}' (ID pending flush: {node.id}) added to workflow {attached_workflow.id}.")
            return node
        except Exception as e:
            wf_dao_log.error(f"Error adding node to workflow {workflow.id}: {e}")
            raise

    @staticmethod
    def get_node_by_id(node_id: str, session: Optional[Session] = None) -> Optional[Node]:
        """Retrieves a Node by its ID."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt = select(Node).where(Node.id == node_id)
            return current_session.execute(stmt).scalar_one_or_none()
        except Exception as e:
            wf_dao_log.error(f"Error fetching node {node_id}: {e}")
            raise

    @staticmethod
    def update_node(node: Node, data: Dict[str, Any], session: Optional[Session] = None) -> Node:
        """Updates an existing node instance with data (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            attached_node = WorkflowDAO._ensure_attached(node, current_session)
            for key, value in data.items():
                if hasattr(attached_node, key) and key not in ['id', 'workflow_id', 'workflow']:
                    setattr(attached_node, key, value)
            wf_dao_log.info(f"Node '{attached_node.name}' (ID: {attached_node.id}) updated in session.")
            return attached_node
        except Exception as e:
            wf_dao_log.error(f"Error updating node {node.id}: {e}")
            raise

    @staticmethod
    def delete_node(node: Node, session: Optional[Session] = None) -> None:
        """Marks a node and its associated links for deletion (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            node_id = node.id
            workflow_id = node.workflow_id
            attached_node = WorkflowDAO._ensure_attached(node, current_session)

            stmt_delete_links = sqlalchemy_delete(Link).where(
                (Link.source == node_id) | (Link.target == node_id),
                Link.workflow_id == workflow_id
            )
            current_session.execute(stmt_delete_links)
            current_session.delete(attached_node)
            wf_dao_log.info(f"Node ID: {node_id} and associated links marked for deletion from workflow {workflow_id}.")
        except Exception as e:
            wf_dao_log.error(f"Error marking node {node.id} for deletion: {e}")
            raise

    @staticmethod
    def add_link_to_workflow(workflow: Workflow, source_node_id: str, target_node_id: str, session: Optional[Session] = None) -> Link:
        """Adds a new link between nodes in a workflow (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            attached_workflow = WorkflowDAO._ensure_attached(workflow, current_session)
            stmt_exists = select(Link).where(
                Link.workflow_id == attached_workflow.id,
                Link.source == source_node_id,
                Link.target == target_node_id
            )
            existing = current_session.execute(stmt_exists).scalar_one_or_none()
            if existing:
                wf_dao_log.warning(f"Link from {source_node_id} to {target_node_id} already exists in workflow {attached_workflow.id}. Returning existing.")
                return existing

            link = Link(source=source_node_id, target=target_node_id, workflow_id=attached_workflow.id)
            attached_workflow.links.append(link)
            current_session.add(link)
            wf_dao_log.info(f"Link from {source_node_id} to {target_node_id} added to workflow {attached_workflow.id}.")
            return link
        except Exception as e:
            wf_dao_log.error(f"Error adding link ({source_node_id}->{target_node_id}) to workflow {workflow.id}: {e}")
            raise

    @staticmethod
    def delete_link(workflow_id: str, source_node_id: str, target_node_id: str, session: Optional[Session] = None) -> bool:
        """Marks a specific link between nodes for deletion (no commit). Returns True if link existed."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt_delete = sqlalchemy_delete(Link).where(
                Link.workflow_id == workflow_id,
                Link.source == source_node_id,
                Link.target == target_node_id
            )
            result = current_session.execute(stmt_delete)
            deleted = result.rowcount > 0
            if deleted:
                wf_dao_log.info(f"Link from {source_node_id} to {target_node_id} marked for deletion from workflow {workflow_id}.")
            else:
                 wf_dao_log.warning(f"Link from {source_node_id} to {target_node_id} not found in workflow {workflow_id} for deletion.")
            return deleted
        except Exception as e:
            wf_dao_log.error(f"Error marking link ({source_node_id}->{target_node_id}) for deletion from workflow {workflow_id}: {e}")
            raise

    @staticmethod
    def set_workflow_var(workflow_id: str, key: str, value: Any, session: Optional[Session] = None) -> WorkflowTempVar:
        """Sets or updates a workflow-scoped temporary variable (no commit)."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt_select = select(WorkflowTempVar).where(WorkflowTempVar.workflow_id == workflow_id, WorkflowTempVar.key == key)
            var = current_session.execute(stmt_select).scalar_one_or_none()

            if var:
                var.value = value
                current_session.add(var)
            else:
                var = WorkflowTempVar(workflow_id=workflow_id, key=key, value=value)
                current_session.add(var)
            return var
        except Exception as e:
            wf_dao_log.error(f"Error setting workflow var '{key}' for workflow {workflow_id}: {e}")
            raise

    @staticmethod
    def get_workflow_var(workflow_id: str, key: str, default: Any = None, session: Optional[Session] = None) -> Any:
        """Gets a workflow-scoped temporary variable."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt = select(WorkflowTempVar.value).where(WorkflowTempVar.workflow_id == workflow_id, WorkflowTempVar.key == key)
            result = current_session.execute(stmt).scalar_one_or_none()
            return result if result is not None else default
        except Exception as e:
            wf_dao_log.error(f"Error getting workflow var '{key}' for workflow {workflow_id}: {e}")
            raise

    @staticmethod
    def clear_workflow_vars(workflow_id: str, session: Optional[Session] = None) -> int:
        """Marks ALL temporary variables for a specific workflow for deletion (no commit). Returns count."""
        current_session = WorkflowDAO._get_session(session)
        try:
            stmt_delete = sqlalchemy_delete(WorkflowTempVar).where(WorkflowTempVar.workflow_id == workflow_id)
            result = current_session.execute(stmt_delete)
            num_deleted = result.rowcount
            if num_deleted > 0:
                wf_dao_log.info(f"Marked {num_deleted} temporary variables for deletion for workflow {workflow_id}")
            return num_deleted
        except Exception as e:
            wf_dao_log.error(f"Error clearing workflow vars for workflow {workflow_id}: {e}")
            raise

    @staticmethod
    def get_session_var(workflow_id: str, session_id: str, key: str, default: Any = None, session: Optional[Session] = None) -> Any:
        """Gets a session-specific temp var."""
        full_key = f'{session_id}_{key}'
        return WorkflowDAO.get_workflow_var(workflow_id, full_key, default, session)

    @staticmethod
    def set_session_var(workflow_id: str, session_id: str, key: str, value: Any, session: Optional[Session] = None) -> WorkflowTempVar:
        """Sets a session-specific temp var (no commit)."""
        full_key = f'{session_id}_{key}'
        return WorkflowDAO.set_workflow_var(workflow_id, full_key, value, session)

    @staticmethod
    def get_node_output_var(workflow_id: str, session_id: str, node_id: str, default: Any = None, session: Optional[Session] = None) -> Any:
        """Gets the output temp var for a specific node in a session."""
        full_key = f'{session_id}_{node_id}_output'
        return WorkflowDAO.get_workflow_var(workflow_id, full_key, default, session)

    @staticmethod
    def set_node_output_var(workflow_id: str, session_id: str, node_id: str, value: Any, session: Optional[Session] = None) -> WorkflowTempVar:
        """Sets the output temp var for a specific node in a session (no commit)."""
        full_key = f'{session_id}_{node_id}_output'
        return WorkflowDAO.set_workflow_var(workflow_id, full_key, value, session)

    @staticmethod
    def clear_session_vars(workflow_id: str, session_id: str, session: Optional[Session] = None) -> int:
        """Marks temporary variables associated with a specific session ID for deletion (no commit). Returns count."""
        current_session = WorkflowDAO._get_session(session)
        prefix = f"{session_id}_"
        try:
            stmt_delete = sqlalchemy_delete(WorkflowTempVar).where(
                WorkflowTempVar.workflow_id == workflow_id,
                WorkflowTempVar.key.like(f"{prefix}%")
            )
            result = current_session.execute(stmt_delete)
            num_deleted = result.rowcount
            if num_deleted > 0:
                wf_dao_log.info(f"Marked {num_deleted} session variables for deletion for session {session_id} in workflow {workflow_id}")
            return num_deleted
        except Exception as e:
            wf_dao_log.error(f"Error clearing session vars for session {session_id}, workflow {workflow_id}: {e}")
            raise