from typing import List, Optional
from app.dao.workflow_dao import WorkflowDAO
from app.dto.workflow_dto import (
    WorkflowCoreDTO, WorkflowDetailDTO, WorkflowCreateDTO, WorkflowSaveDTO,
    NodeDTO, LinkDTO, NodeUpdateDTO
)
from app.models.workflow import Workflow, Node, Link
from app.utils.utils import create_logger
from app.extensions import db
from app.context import context

wf_service_log = create_logger(__name__, entity_name='WORKFLOW_SERVICE', level=context.log_level)

class WorkflowService:
    """Service layer for managing Workflows."""

    def _node_to_dto(self, node: Node) -> NodeDTO:
        return NodeDTO(
            id=node.id,
            name=node.name,
            node_type=node.node_type,
            node_subtype=node.node_subtype,
            on=node.on,
            interface=node.interface,
            code=node.code,
            handler=node.handler,
            static_input=node.static_input,
            workflow_id=node.workflow_id
        )

    def _link_to_dto(self, link: Link) -> LinkDTO:
        return LinkDTO(
            source=link.source,
            target=link.target
        )

    def _workflow_to_detail_dto(self, workflow: Workflow) -> WorkflowDetailDTO:
        nodes_dict = {node.id: self._node_to_dto(node) for node in workflow.nodes}
        links_list = [self._link_to_dto(link) for link in workflow.links]
        return WorkflowDetailDTO(
            id=workflow.id,
            name=workflow.name,
            graph=workflow.graph,
            nodes=nodes_dict,
            links=links_list
        )

    def _workflow_to_core_dto(self, workflow: Workflow) -> WorkflowCoreDTO:
         return WorkflowCoreDTO(
             id=workflow.id,
             name=workflow.name
         )

    def get_workflow_detail(self, workflow_id: str) -> Optional[WorkflowDetailDTO]:
        """Retrieves detailed information about a workflow."""
        workflow = WorkflowDAO.get_workflow_by_id(workflow_id, load_relations=True)
        if not workflow:
            wf_service_log.warning(f"Workflow detail request failed: Workflow {workflow_id} not found.")
            return None
        return self._workflow_to_detail_dto(workflow)

    def get_workflow_list(self) -> List[WorkflowCoreDTO]:
        """Retrieves a list of basic workflow information."""
        workflow_ids = WorkflowDAO.get_workflow_list_ids()
        workflows_dto = []
        for wf_id in workflow_ids:
            workflow = WorkflowDAO.get_workflow_by_id(wf_id, load_relations=False)
            if workflow:
                workflows_dto.append(self._workflow_to_core_dto(workflow))
            else:
                 wf_service_log.warning(f"Workflow {wf_id} found in list but couldn't be fetched for core info.")
        return workflows_dto

    def create_workflow(self, create_dto: WorkflowCreateDTO) -> Optional[WorkflowCoreDTO]:
        """Creates a new workflow."""
        try:
            workflow = WorkflowDAO.create_workflow(name=create_dto.name, graph=create_dto.graph)
            if not workflow:
                return None
            db.session.commit()
            wf_service_log.info(f"Workflow '{workflow.name}' created successfully with ID: {workflow.id}")
            return self._workflow_to_core_dto(workflow)
        except Exception as e:
            wf_service_log.exception(f"Error creating workflow '{create_dto.name}': {e}")
            db.session.rollback()
            return None

    def save_workflow(self, save_dto: WorkflowSaveDTO) -> Optional[WorkflowCoreDTO]:
        """Saves (creates or updates) a workflow structure."""
        try:
            if save_dto.id:
                workflow = WorkflowDAO.get_workflow_by_id(save_dto.id, load_relations=True)
                if not workflow:
                    wf_service_log.error(f"Save failed: Workflow {save_dto.id} not found for update.")
                    return None

                update_data = save_dto.model_dump(exclude_unset=True, exclude_none=True)

                if update_data:
                    WorkflowDAO.update_workflow(workflow, update_data)

                db.session.commit()
                # Log using the potentially updated name from update_data or the existing workflow name
                log_name = update_data.get('name', workflow.name)
                wf_service_log.info(f"Workflow '{log_name}' (ID: {save_dto.id}) updated successfully.")
                updated_workflow = WorkflowDAO.get_workflow_by_id(save_dto.id, load_relations=False)
                return self._workflow_to_core_dto(updated_workflow) if updated_workflow else None

            else:
                new_workflow = WorkflowDAO.create_workflow(name=save_dto.name, graph=save_dto.graph)
                if not new_workflow:
                    return None

                db.session.commit()
                wf_service_log.info(f"Workflow '{new_workflow.name}' created successfully with ID: {new_workflow.id} during save operation.")
                return self._workflow_to_core_dto(new_workflow)

        except Exception as e:
            wf_service_log.exception(f"Error saving workflow (ID: {save_dto.id}): {e}")
            db.session.rollback()
            return None


    def delete_workflow(self, workflow_id: str) -> bool:
        """Deletes a workflow."""
        try:
            workflow = WorkflowDAO.get_workflow_by_id(workflow_id, load_relations=False)
            if not workflow:
                wf_service_log.warning(f"Delete failed: Workflow {workflow_id} not found.")
                return False
            WorkflowDAO.delete_workflow(workflow)
            db.session.commit()
            wf_service_log.info(f"Workflow {workflow_id} deleted successfully.")
            return True
        except Exception as e:
            wf_service_log.exception(f"Error deleting workflow {workflow_id}: {e}")
            db.session.rollback()
            return False

    def add_node(self, workflow_id: str, node_dto: NodeDTO) -> Optional[NodeDTO]:
        """Adds a node to a workflow."""
        try:
            workflow = WorkflowDAO.get_workflow_by_id(workflow_id, load_relations=False)
            if not workflow:
                wf_service_log.error(f"Add node failed: Workflow {workflow_id} not found.")
                return None

            node_data = node_dto.__dict__
            node_data['workflow_id'] = workflow_id

            new_node = WorkflowDAO.add_node_to_workflow(workflow, node_data)
            if not new_node:
                 return None
            db.session.commit()
            wf_service_log.info(f"Node '{new_node.name}' added successfully to workflow {workflow_id} with ID: {new_node.id}")
            return self._node_to_dto(new_node)
        except Exception as e:
            wf_service_log.exception(f"Error adding node to workflow {workflow_id}: {e}")
            db.session.rollback()
            return None

    def update_node(self, node_id: str, node_update_dto: NodeUpdateDTO) -> bool:
        """Updates an existing node with only the provided fields."""
        try:
            node = WorkflowDAO.get_node_by_id(node_id)
            if not node:
                wf_service_log.error(f"Update node failed: Node {node_id} not found.")
                return False

            # Get only the fields that were explicitly set in the request DTO
            update_data = node_update_dto.model_dump(exclude_unset=True)

            if not update_data:
                 wf_service_log.info(f"No fields provided to update for node {node_id}.")
                 return True # Nothing to update, consider it a success

            WorkflowDAO.update_node(node, update_data)
            db.session.commit()
            wf_service_log.info(f"Node {node_id} updated successfully.")
            return True
        except Exception as e:
            wf_service_log.exception(f"Error updating node {node_id}: {e}")
            db.session.rollback()
            return False

    def delete_node(self, node_id: str) -> bool:
        """Deletes a node."""
        try:
            node = WorkflowDAO.get_node_by_id(node_id)
            if not node:
                wf_service_log.warning(f"Delete node failed: Node {node_id} not found.")
                return False
            WorkflowDAO.delete_node(node)
            db.session.commit()
            wf_service_log.info(f"Node {node_id} deleted successfully.")
            return True
        except Exception as e:
            wf_service_log.exception(f"Error deleting node {node_id}: {e}")
            db.session.rollback()
            return False

    def get_node_content(self, node_id: str) -> Optional[NodeDTO]:
        """Retrieves the content/details of a specific node."""
        node = WorkflowDAO.get_node_by_id(node_id)
        if not node:
            wf_service_log.warning(f"Get node content failed: Node {node_id} not found.")
            return None
        return self._node_to_dto(node)

    def add_link(self, workflow_id: str, link_dto: LinkDTO) -> bool:
        """Adds a link between two nodes in a workflow."""
        try:
            workflow = WorkflowDAO.get_workflow_by_id(workflow_id, load_relations=False)
            if not workflow:
                wf_service_log.error(f"Add link failed: Workflow {workflow_id} not found.")
                return False

            source_node = WorkflowDAO.get_node_by_id(link_dto.source)
            target_node = WorkflowDAO.get_node_by_id(link_dto.target)
            if not source_node or source_node.workflow_id != workflow_id:
                wf_service_log.error(f"Add link failed: Source node {link_dto.source} not found in workflow {workflow_id}.")
                return False
            if not target_node or target_node.workflow_id != workflow_id:
                wf_service_log.error(f"Add link failed: Target node {link_dto.target} not found in workflow {workflow_id}.")
                return False

            link = WorkflowDAO.add_link_to_workflow(workflow, link_dto.source, link_dto.target)
            if link:
                db.session.commit()
                wf_service_log.info(f"Link {link_dto.source}->{link_dto.target} added successfully to workflow {workflow_id}.")
                return True
            else:
                wf_service_log.warning(f"Link {link_dto.source}->{link_dto.target} might already exist or failed to add without exception in workflow {workflow_id}.")
                return False
        except Exception as e:
            wf_service_log.exception(f"Error adding link {link_dto.source}->{link_dto.target} to workflow {workflow_id}: {e}")
            db.session.rollback()
            return False

    def delete_link(self, workflow_id: str, link_dto: LinkDTO) -> bool:
        """Deletes a link between two nodes."""
        try:
            deleted = WorkflowDAO.delete_link(workflow_id, link_dto.source, link_dto.target)
            if deleted:
                db.session.commit()
                wf_service_log.info(f"Link {link_dto.source}->{link_dto.target} deleted successfully from workflow {workflow_id}.")
            # else: # DAO already logs a warning if not found
            return deleted
        except Exception as e:
            wf_service_log.exception(f"Error deleting link {link_dto.source}->{link_dto.target} from workflow {workflow_id}: {e}")
            db.session.rollback()
            return False