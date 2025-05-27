from threading import RLock
import uuid
from collections import defaultdict
from typing import Dict, Any, Optional, List
from flask import Flask
from lupa import LuaRuntime

from app.models.workflow import Node, Link, NODE_DEFAULT_HANDLERS, PYTHON_NODE_GLOBALS
from app.models.utils import ACLMessage, MessageBroker
from app.dao.workflow_dao import WorkflowDAO
from app.events import TriggerType
from app.utils.utils import run_thread_with_context, create_logger
from app.extensions import db
from app.context import context

wf_runtime_log = create_logger(__name__, entity_name='WORKFLOW_RUNTIME', level=context.log_level)

class WorkflowRuntime:
    """Manages the runtime execution state of a workflow instance."""

    def __init__(self, workflow_id: str, agent_id: str, initial_vars: Dict[str, Any], broker: MessageBroker, app_instance: Flask):
        self.workflow_id: str = workflow_id
        self.agent_id: str = agent_id
        self.vars: Dict[str, Any] = initial_vars
        self.broker: MessageBroker = broker
        self.app_instance: Flask = app_instance

        self.execution_state: Dict[str, Any] = {
            'completed': defaultdict(set),
            'merge_counters': defaultdict(lambda: defaultdict(int)),
            'stop_path_requested': defaultdict(bool),
            'lock': RLock(),
            'session_stop_requested': False,
            'active_threads': 0
        }
        self.workflow_structure: Optional[Dict] = None
        self.stop_requested_globally: bool = False

        wf_runtime_log.info(f"WorkflowRuntime initialized for Workflow ID: {self.workflow_id}, Agent ID: {self.agent_id}")

    def _load_workflow_structure(self) -> bool:
        """Loads and caches the workflow structure (nodes, links) using the DAO."""
        if self.workflow_structure:
            return True
        with self.app_instance.app_context():
            workflow = WorkflowDAO.get_workflow_by_id(self.workflow_id, load_relations=True)
            if not workflow:
                wf_runtime_log.error(f"Failed to load workflow structure for {self.workflow_id}.")
                return False

            self.workflow_structure = {
                'nodes': {node.id: node for node in workflow.nodes},
                'links': workflow.links
            }
            wf_runtime_log.debug(f"Loaded structure for workflow {self.workflow_id}: {len(self.workflow_structure['nodes'])} nodes, {len(self.workflow_structure['links'])} links.")
            return True

    def _get_node(self, node_id: str) -> Optional[Node]:
        """Gets a node object from the cached structure."""
        wf_runtime_log.debug(f"Entering _get_node for node_id: {node_id}")
        if not self.workflow_structure:
            if not self._load_workflow_structure():
                wf_runtime_log.error(f"_get_node: Failed to load structure while getting node {node_id}")
                return None
        node = self.workflow_structure['nodes'].get(node_id)
        wf_runtime_log.debug(f"_get_node: Returning {'node object' if node else 'None'} for node_id: {node_id}")
        return node

    def _get_links(self) -> List[Link]:
        """Gets the list of link objects from the cached structure."""
        if not self.workflow_structure:
            if not self._load_workflow_structure():
                return []
        return self.workflow_structure['links']

    def _get_incoming_links_count(self, node_id: str) -> int:
        """Calculates the number of incoming links for a node."""
        return sum(1 for link in self._get_links() if link.target == node_id)

    def _run_in_thread(self, target, execution_id: str, args=()):
        """Helper to run a target function in a new thread with app context."""
        with self.execution_state['lock']:
            self.execution_state['active_threads'] += 1
            wf_runtime_log.debug(f"[{execution_id}] Incrementing active threads to {self.execution_state['active_threads']} for target {target.__name__}")

        full_args = (execution_id,) + args

        def target_wrapper(*wrapper_args):
            current_execution_id = wrapper_args[0]
            target_actual_args = wrapper_args[1:]
            wf_runtime_log.debug(f"[{current_execution_id}] Entering target_wrapper for {target.__name__} with args: {target_actual_args}")
            try:
                with self.app_instance.app_context():
                    target(current_execution_id, *target_actual_args)
            except Exception as e:
                 wf_runtime_log.exception(f"[{current_execution_id}] Unhandled exception in thread target {target.__name__}: {e}")
            finally:
                cleanup_needed = False
                with self.execution_state['lock']:
                    self.execution_state['active_threads'] -= 1
                    wf_runtime_log.debug(f"[{current_execution_id}] Decrementing active threads to {self.execution_state['active_threads']} after target {target.__name__}")
                    if self.execution_state['active_threads'] == 0 and not self.execution_state['session_stop_requested']:
                        cleanup_needed = True
                        wf_runtime_log.info(f"[{current_execution_id}] Session has no more active threads. Triggering cleanup.")
                if cleanup_needed:
                    with self.app_instance.app_context():
                        self._cleanup_session_vars(current_execution_id)
                        self.execution_state['completed'].pop(current_execution_id, None)
                        self.execution_state['merge_counters'].pop(current_execution_id, None)
                        self.execution_state['stop_path_requested'].pop(current_execution_id, None)


        wf_runtime_log.debug(f"[{execution_id}] Preparing to call run_thread_with_context for target {target.__name__} with args: {args}")
        thread = run_thread_with_context(
            target=target_wrapper,
            app=self.app_instance,
            args=full_args
        )
        return thread

    def _request_session_stop(self):
        """Requests the current execution session to stop."""
        with self.execution_state['lock']:
            if not self.execution_state.get('session_stop_requested', False):
                self.execution_state['session_stop_requested'] = True
                wf_runtime_log.info("Session stop requested.")


    def _cleanup_session_vars(self, execution_id: str):
        """Cleans up temporary variables associated with a specific execution ID."""
        wf_runtime_log.debug(f"[{execution_id}] Attempting to clean up session variables.")
        try:
            num_deleted = WorkflowDAO.clear_session_vars(self.workflow_id, execution_id)
            db.session.commit()
            wf_runtime_log.info(f"[{execution_id}] Successfully cleaned up {num_deleted} session variables and committed.")
        except Exception as e:
            db.session.rollback()
            wf_runtime_log.exception(f"[{execution_id}] Error cleaning up session variables. Rolled back transaction: {e}")

    def _find_node_by_type_and_subtype(self, node_type: str, node_subtype: str) -> Optional[Node]:
        """Finds the first active node matching the type and subtype."""
        if not self.workflow_structure:
            if not self._load_workflow_structure():
                return None
        return next((node for node in self.workflow_structure['nodes'].values()
                     if node.node_type == node_type and node.node_subtype == node_subtype and node.on), None)

    def execute_trigger(self, trigger_type: str, message: Optional[ACLMessage] = None):
        """Finds and executes the appropriate trigger node."""
        if not self._load_workflow_structure():
            wf_runtime_log.error(f"Cannot execute trigger '{trigger_type}', failed to load workflow structure.")
            return

        trigger_node = self._find_node_by_type_and_subtype('trigger', trigger_type)
        
        if not trigger_node:
            if self.agent_id is not None and isinstance(self.agent_id, str):
                self_topic = trigger_type.replace(f'/agent:{self.agent_id}', '/self', 1)
                trigger_node = self._find_node_by_type_and_subtype('trigger', self_topic)
        
        if not trigger_node:
            wf_runtime_log.debug(f"No active trigger node found for type '{trigger_type}' in workflow {self.workflow_id}.")
            return

        execution_id = str(uuid.uuid4())
        wf_runtime_log.info(f"[{execution_id}] Executing trigger '{trigger_type}' (Node ID: {trigger_node.id}).")
        self._run_in_thread(
            target=self._process_node,
            execution_id=execution_id,
            args=(trigger_node.id, message)
        )

    def execute_init(self):
        """Executes the INIT trigger."""
        self.execute_trigger(TriggerType.INIT)

    def execute_cyclic(self):
        """Executes the CYCLIC trigger."""
        with self.execution_state['lock']:
            if self.execution_state['session_stop_requested'] or self.stop_requested_globally:
                return
        self.execute_trigger(TriggerType.CYCLIC)

    def execute_stop(self):
        """Executes the STOP trigger and requests session cleanup."""
        wf_runtime_log.info(f"Executing STOP trigger for workflow {self.workflow_id}.")
        self.stop_requested_globally = True
        self._request_session_stop()

        try:
            with self.app_instance.app_context():
                num_deleted = WorkflowDAO.clear_workflow_vars(self.workflow_id)
                db.session.commit()
                wf_runtime_log.info(f"Cleared {num_deleted} workflow variables for workflow {self.workflow_id} during stop.")
        except Exception as e:
            db.session.rollback()
            wf_runtime_log.exception(f"Error clearing workflow variables for workflow {self.workflow_id} during stop: {e}")


        if not self._load_workflow_structure():
             wf_runtime_log.error("Cannot execute STOP trigger node, failed to load workflow structure.")
             return

        stop_trigger_node = self._find_node_by_type_and_subtype('trigger', TriggerType.STOP)

        if stop_trigger_node:
             stop_execution_id = str(uuid.uuid4())
             wf_runtime_log.info(f"[{stop_execution_id}] Executing STOP trigger node {stop_trigger_node.id}.")
             self._run_in_thread(
                 target=self._process_node,
                 execution_id=stop_execution_id,
                 args=(stop_trigger_node.id, None)
             )
        else:
            wf_runtime_log.info("No explicit STOP trigger found. Cleanup will occur when active threads complete.")


    def _process_node(self, execution_id: str, node_id: str, message: Optional[ACLMessage]):
        wf_runtime_log.debug(f"[{execution_id}] Entering _process_node for node_id: {node_id}")
        """
        Processes a single node within a specific execution flow (identified by execution_id).
        Handles node execution, branching, merging, and session variable management via DAO.
        Runs within a thread managed by _run_in_thread.
        """
        node = self._get_node(node_id)
        if not node:
            wf_runtime_log.error(f"[{execution_id}] Node {node_id} not found in workflow {self.workflow_id}. Aborting processing.")
            return

        should_execute = False
        with self.execution_state['lock']:
            if self.stop_requested_globally:
                wf_runtime_log.debug(f"[{execution_id}] Global stop requested. Node {node_id} execution skipped.")
                return
            if self.execution_state['session_stop_requested']:
                wf_runtime_log.debug(f"[{execution_id}] Session stop requested before node {node_id}. Execution skipped.")
                return

            if node_id in self.execution_state['completed'][execution_id]:
                wf_runtime_log.debug(f"[{execution_id}] Node {node_id} already completed in this execution. Skipping.")
                return

            incoming_links_count = self._get_incoming_links_count(node_id)
            prerequisites_met = True
            if incoming_links_count > 1:
                current_merge_count = self.execution_state['merge_counters'][execution_id][node_id] + 1
                self.execution_state['merge_counters'][execution_id][node_id] = current_merge_count
                wf_runtime_log.debug(f"[{execution_id}] Merge counter for node {node_id} incremented to {current_merge_count}/{incoming_links_count}.")
                if current_merge_count < incoming_links_count:
                    prerequisites_met = False

            if prerequisites_met:
                self.execution_state['completed'][execution_id].add(node_id)
                should_execute = True
                wf_runtime_log.debug(f"[{execution_id}] Prerequisites met for node {node_id}. Proceeding to execute.")
            else:
                 wf_runtime_log.debug(f"[{execution_id}] Prerequisites not met for node {node_id}. Execution deferred.")


        if not should_execute:
            return

        node_output = None
        execution_succeeded = False
        execution_succeeded = False
        try:
            # --- Helper functions (closures) ---
            def request_stop_path():
                """Signals that the current execution path should stop after this node."""
                with self.execution_state['lock']:
                    if not self.execution_state['session_stop_requested'] and not self.stop_requested_globally:
                        self.execution_state['stop_path_requested'][execution_id + node_id] = True
                        wf_runtime_log.info(f"[{execution_id}] Stop path requested by node {node_id}.")

            if node.on:
                with self.execution_state['lock']:
                    if self.execution_state['session_stop_requested'] or self.stop_requested_globally:
                        wf_runtime_log.debug(f"[{execution_id}] Stop requested just before executing node {node_id}.")
                        return

                wf_runtime_log.info(f"[{execution_id}] Executing node '{node.name}' (ID: {node_id}, Type: {node.node_type}/{node.node_subtype})")

                def write_raw_output(output_data_for_dao: Any):
                    """Writes the provided raw data as the node's output, after checking stop conditions."""
                    with self.execution_state['lock']:
                        if self.execution_state['session_stop_requested'] or self.stop_requested_globally:
                            key_info = f"(key: {output_data_for_dao.get('key')})" if isinstance(output_data_for_dao, dict) and 'key' in output_data_for_dao else ""
                            wf_runtime_log.warning(f"[{execution_id}] Stop requested, raw output from node {node_id} {key_info} discarded.")
                            return
                    WorkflowDAO.set_node_output_var(self.workflow_id, execution_id, node_id, output_data_for_dao)
                    # wf_runtime_log.debug(f"[{execution_id}] Node {node_id} raw output set: {output_data_for_dao}")

                def write_output(key: str, output_value: Any):
                    """Writes a key-value pair as the node's output."""
                    output_data = {'key': key, 'value': output_value}
                    write_raw_output(output_data)

                def get_session_var(key: str, default: Any = None):
                    return WorkflowDAO.get_session_var(self.workflow_id, execution_id, key, default)

                def set_session_var(key: str, value: Any):
                    with self.execution_state['lock']:
                         if self.execution_state['session_stop_requested'] or self.stop_requested_globally:
                             wf_runtime_log.warning(f"[{execution_id}] Stop requested, set_session_var for key '{key}' ignored.")
                             return
                    WorkflowDAO.set_session_var(self.workflow_id, execution_id, key, value)

                def get_input(key: str, default: Any = None) -> Any:
                    return node.static_input.get(key, default)

                def get_parent_output() -> List[Any]:
                    """
                    Retrieves all 'effective' outputs from direct parent nodes.
                    If a parent's output is an 'aggregated_parent_outputs' structure,
                    its contained items are unpacked into the returned list.
                    Returns a list of output items (usually dicts like {'key': k, 'value': v}).
                    """
                    parent_ids = [link.source for link in self._get_links() if link.target == node_id]
                    effective_outputs = []
                    for parent_id in parent_ids:
                        parent_output_item = WorkflowDAO.get_node_output_var(self.workflow_id, execution_id, parent_id)
                        if parent_output_item is not None:
                            if isinstance(parent_output_item, dict) and \
                               parent_output_item.get('key') == 'aggregated_parent_outputs' and \
                               isinstance(parent_output_item.get('value'), list):
                                wf_runtime_log.debug(f"[{execution_id}] Unpacking 'aggregated_parent_outputs' from parent {parent_id} for node {node_id}.")
                                effective_outputs.extend(parent_output_item['value'])
                            else:
                                effective_outputs.append(parent_output_item)
                    return effective_outputs

                def get_parent_output_by_key(key: str) -> List[Any]:
                    """
                    Retrieves values from parent outputs that match the given key.
                    Considers 'aggregated_parent_outputs' from direct parents.
                    """
                    all_effective_parent_outputs = get_parent_output()
                    matching_values = []
                    for item in all_effective_parent_outputs:
                        if isinstance(item, dict) and item.get('key') == key:
                            matching_values.append(item.get('value'))
                    return matching_values
                
                def get_single_parent_output_by_key(key: str, default: Any = None) -> Any:
                    """
                    Retrieves a single value from parent outputs matching the key.
                    Considers 'aggregated_parent_outputs'. If multiple values for the key
                    are found across all effective parent outputs, logs a warning and returns default.
                    """
                    matching_values = get_parent_output_by_key(key)

                    if len(matching_values) == 1:
                        return matching_values[0]
                    elif len(matching_values) == 0:
                        return default
                    else:
                        wf_runtime_log.warning(f"[{execution_id}] Found multiple ({len(matching_values)}) effective parent output values for key '{key}' when expecting single for node {node_id}. Returning default.")
                        return default

                def pass_output():
                    """
                    Passes 'effective' output(s) from parent node(s) to the current node.
                    - If one effective parent output, current node's output becomes identical to it.
                    - If multiple effective parent outputs, current node's output becomes a new
                      'aggregated_parent_outputs' structure containing them.
                    """
                    wf_runtime_log.debug(f"[{execution_id}] Node {node_id} attempting to pass parent outputs.")
                    effective_parent_outputs = get_parent_output()

                    if not effective_parent_outputs:
                        wf_runtime_log.debug(f"[{execution_id}] Node {node_id} has no effective parent outputs to pass.")
                        return

                    if len(effective_parent_outputs) == 1:
                        single_item = effective_parent_outputs[0]
                        wf_runtime_log.debug(f"[{execution_id}] Node {node_id} passing single effective parent output directly: {single_item}")
                        write_raw_output(single_item)
                    else:
                        wf_runtime_log.debug(f"[{execution_id}] Node {node_id} re-aggregating {len(effective_parent_outputs)} effective parent outputs.")
                        aggregated_output = {'key': 'aggregated_parent_outputs', 'value': effective_parent_outputs}
                        write_raw_output(aggregated_output)

                # --- Node Execution Logic ---
                if node.node_type == 'custom' or node.node_type == 'trigger':
                    if node.code:
                        if node.node_subtype == 'lua':
                            lua = LuaRuntime(unpack_returned_tuples=True)
                            lua_globals = lua.globals()
                            lua_globals.vars = self.vars
                            lua_globals.execution_id = execution_id
                            lua_globals.message = message
                            lua_globals.agent_id = self.agent_id
                            lua_globals.node_id = node_id
                            lua_globals.broker = self.broker
                            lua_globals.write_output = write_output
                            lua_globals.write_raw_output = write_raw_output
                            lua_globals.get_session_var = get_session_var
                            lua_globals.set_session_var = set_session_var
                            lua_globals.static_input = node.static_input
                            lua_globals.get_input = get_input
                            lua_globals.get_parent_output = get_parent_output
                            lua_globals.get_parent_output_by_key = get_parent_output_by_key
                            lua_globals.get_single_parent_output_by_key = get_single_parent_output_by_key
                            lua_globals.request_session_stop = self._request_session_stop
                            lua_globals.request_stop_path = request_stop_path
                            lua_globals.pass_output = pass_output
                            for k, v in PYTHON_NODE_GLOBALS.items():
                                if isinstance(v, (str, int, float, bool, dict, list, tuple)) or callable(v):
                                    try:
                                        lua_globals[k] = v
                                    except Exception:
                                        continue
                            lua.execute(node.code)
                        else:
                            exec_globals = {
                                'vars': self.vars,
                                'execution_id': execution_id,
                                'message': message,
                                'agent_id': self.agent_id,
                                'node_id': node_id,
                                'broker': self.broker,
                                'write_output': write_output,
                                'write_raw_output': write_raw_output,
                                'get_session_var': get_session_var,
                                'set_session_var': set_session_var,
                                'static_input': node.static_input,
                                'get_input': get_input,
                                'get_parent_output': get_parent_output,
                                'get_parent_output_by_key': get_parent_output_by_key,
                                'get_single_parent_output_by_key': get_single_parent_output_by_key,
                                'request_session_stop': self._request_session_stop,
                                'request_stop_path': request_stop_path,
                                'pass_output': pass_output,
                                **PYTHON_NODE_GLOBALS
                            }
                            exec(node.code, exec_globals)

                        node_output = WorkflowDAO.get_node_output_var(self.workflow_id, execution_id, node_id)

                elif node.handler:
                    handler_func = NODE_DEFAULT_HANDLERS.get(node.handler)
                    if handler_func:
                         handler_func(
                             workflow_id=self.workflow_id,
                             execution_id=execution_id,
                             agent_id=self.agent_id, node_id=node_id,
                             message=message, vars=self.vars,
                             static_input=node.static_input, broker=self.broker,
                             write_output=write_output, write_raw_output=write_raw_output, get_session_var=get_session_var, set_session_var=set_session_var,
                             get_input=get_input, get_parent_output=get_parent_output, get_parent_output_by_key=get_parent_output_by_key, get_single_parent_output_by_key=get_single_parent_output_by_key,
                             request_session_stop=self._request_session_stop,
                             request_stop_path=request_stop_path,
                             pass_output=pass_output,
                             # Workflow var access helpers (if uncommented, would use session_id)
                             # get_workflow_var=lambda k, d=None: WorkflowDAO.get_workflow_var(self.workflow_id, f'workflow_{k}', d),
                             # set_workflow_var=lambda k, v: WorkflowDAO.set_workflow_var(self.workflow_id, f'workflow_{k}', v)
                         )
                         node_output = WorkflowDAO.get_node_output_var(self.workflow_id, execution_id, node_id)
                    else:
                         wf_runtime_log.warning(f"[{execution_id}] No default handler found for key '{node.handler}' on node {node_id}.")

                if node.node_type == 'trigger':
                    output_value = node_output.get('value') if isinstance(node_output, dict) else node_output
                    if output_value is False:
                        wf_runtime_log.debug(f"[{execution_id}] Trigger node {node.name} returned False. Stopping this execution path.")
                        return

            else:
                wf_runtime_log.debug(f"[{execution_id}] Node '{node.name}' (ID: {node_id}) is disabled. Skipping execution.")
            execution_succeeded = True

        except Exception as node_exec_error:
            db.session.rollback()
            wf_runtime_log.exception(f"[{execution_id}] Error during execution of node {node.name} ({node_id}). Rolled back: {node_exec_error}")
            return

        # --- Post-execution: Commit and Schedule Next Nodes ---
        if execution_succeeded:
            try:
                db.session.commit()
                wf_runtime_log.debug(f"[{execution_id}] Successfully committed changes after node {node_id}.")

                with self.execution_state['lock']:
                    stop_path_req = self.execution_state['stop_path_requested'].pop(execution_id + node_id, False)
                    if stop_path_req:
                        wf_runtime_log.debug(f"[{execution_id}] Stop path was requested. No further nodes scheduled from this path after node {node_id}.")
                        return

                    if self.execution_state['session_stop_requested'] or self.stop_requested_globally:
                        wf_runtime_log.debug(f"[{execution_id}] Stop requested after processing node {node_id}. No further nodes scheduled from this path.")
                        return

                    outgoing_links = [link.target for link in self._get_links() if link.source == node_id]
                    wf_runtime_log.debug(f"[{execution_id}] Node {node_id} finished. Found outgoing links to: {outgoing_links}")

                    for next_node_id in outgoing_links:
                        is_completed = next_node_id in self.execution_state['completed'][execution_id]
                        wf_runtime_log.debug(f"[{execution_id}] Loop: Checking next node: {next_node_id}. Completed in this execution? {is_completed}")
                        if is_completed:
                             wf_runtime_log.debug(f"[{execution_id}] Loop: Node {next_node_id} already completed in this execution. Skipping scheduling.")
                             continue

                        wf_runtime_log.debug(f"[{execution_id}] Loop: Scheduling next node {next_node_id} for processing.")
                        self._run_in_thread(
                            target=self._process_node,
                            execution_id=execution_id,
                            args=(next_node_id, message)
                        )
                        wf_runtime_log.debug(f"[{execution_id}] Loop: Called _run_in_thread for {next_node_id}")

            except Exception as commit_error:
                db.session.rollback()
                wf_runtime_log.exception(f"[{execution_id}] Error committing changes after node {node.name} ({node_id}). Rolled back: {commit_error}")