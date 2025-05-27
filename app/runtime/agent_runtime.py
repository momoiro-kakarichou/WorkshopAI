import queue
import threading
import time
from typing import Dict, Any, List, Callable, Optional, Tuple
from flask import Flask

from app.scheduler import CyclicTaskManager
from app.events import TriggerType
from app.dao.workflow_dao import WorkflowDAO
from app.runtime.workflow_runtime import WorkflowRuntime
from app.models.utils import ACLMessage, MessageBroker
from app.utils.utils import run_thread_with_context, create_logger
from app.context import context

agent_log = create_logger(__name__, entity_name='AGENT_RUNTIME', level=context.log_level)

class AgentRuntime:
    """Manages the runtime state and execution of a single agent instance."""

    def __init__(self, agent_id: str, agent_name: str, workflow_id: str, initial_vars: Dict[str, Any], app_instance: Flask):
        self.id: str = agent_id
        self.name: str = agent_name
        self.workflow_id: str = workflow_id
        self.vars: Dict[str, Any] = initial_vars
        self.app_instance: Flask = app_instance

        self.task_threads: List[threading.Thread] = []
        self.is_started: bool = False
        self.cyclic_task_id: str = f'{self.id}_cyclic_task'
        self.message_queue: queue.Queue[Optional[Tuple[str, ACLMessage]]] = queue.Queue()
        self.processing_thread: Optional[threading.Thread] = None
        self.broker: Optional[MessageBroker] = None
        self.cyclic_task_manager: Optional[CyclicTaskManager] = None
        self.workflow_runtime: Optional[WorkflowRuntime] = None

        base_subscriptions = [
            f"/agent:{self.id}",
            f"/agent:{self.name}",
            "/system/#",
            "/broadcast"
        ]
        self.subscriptions: List[str] = list(set(base_subscriptions))
        self.message_handler: Callable[[str, ACLMessage], None] = self._enqueue_message

        agent_log.info(f"AgentRuntime initialized for {self.name} (ID: {self.id})")


    def get_runtime_info(self) -> Dict[str, Any]:
        """Returns the current runtime status."""
        return {
            'is_started': self.is_started
        }

    def update_vars(self, new_vars: Dict[str, Any]):
        """Updates the runtime variables."""
        self.vars = new_vars
        agent_log.debug(f"{self.name}: Runtime variables updated.")


    def start(self, broker: MessageBroker, cyclic_task_manager: CyclicTaskManager):
        """Starts the agent's runtime execution."""
        if self.is_started:
            agent_log.warning(f"{self.name}: Start called but already started.")
            return

        agent_log.info(f"{self.name}: Starting...")
        self.is_started = True
        self.broker = broker
        self.cyclic_task_manager = cyclic_task_manager

        with self.app_instance.app_context():
            workflow = WorkflowDAO.get_workflow_by_id(self.workflow_id, load_relations=True)
            if not workflow:
                agent_log.error(f"{self.name}: Workflow {self.workflow_id} not found. Cannot start.")
                self.is_started = False
                return

            trigger_topics = [
                node.node_subtype for node in workflow.nodes
                if node.node_type == 'trigger' and node.node_subtype and node.node_subtype not in [TriggerType.INIT, TriggerType.STOP, TriggerType.CYCLIC]
            ]
            trigger_topics = [t.replace('/self', f'/agent:{self.id}', 1) if t.startswith('/self') else t for t in trigger_topics]
            self.subscriptions = list(set(self.subscriptions + trigger_topics))

            has_cyclic_handler = any(node.node_type == 'trigger' and node.node_subtype == TriggerType.CYCLIC and node.on for node in workflow.nodes)

        self.workflow_runtime = WorkflowRuntime(
            workflow_id=self.workflow_id,
            agent_id=self.id,
            initial_vars=self.vars,
            broker=broker,
            app_instance=self.app_instance
        )

        agent_log.info(f"{self.name}: Executing INIT trigger via WorkflowRuntime.")
        self.workflow_runtime.execute_init()

        if has_cyclic_handler:
             agent_log.info(f"{self.name}: Registering cyclic task '{self.cyclic_task_id}'.")
             self.cyclic_task_manager.add_task(self.cyclic_task_id, self._run_cyclic_task, 0.5) # Interval 0.5s

        agent_log.info(f"{self.name}: Subscribing to topics: {self.subscriptions}")
        for topic in self.subscriptions:
             try:
                 self.broker.subscribe(topic, self.message_handler)
             except Exception as e:
                  agent_log.error(f"{self.name}: Failed to subscribe to topic '{topic}': {e}")

        agent_log.info(f"{self.name}: Starting message processing thread.")
        self.processing_thread = self._run_in_thread(target=self._message_processing_loop)
        self.task_threads.append(self.processing_thread)

        agent_log.info(f"{self.name} started successfully.")


    def stop(self):
        """Stops the agent's runtime execution and cleans up resources."""
        if not self.is_started:
            agent_log.warning(f"{self.name}: Stop called but not started.")
            return

        agent_log.info(f"{self.name}: Stopping...")
        self.is_started = False

        if self.workflow_runtime:
            agent_log.info(f"{self.name}: Executing STOP trigger via WorkflowRuntime.")
            self.workflow_runtime.execute_stop()
        else:
            agent_log.warning(f"{self.name}: WorkflowRuntime not initialized during stop sequence.")


        if self.cyclic_task_manager:
             agent_log.info(f"{self.name}: Removing cyclic task {self.cyclic_task_id}.")
             try:
                 self.cyclic_task_manager.remove_task(self.cyclic_task_id)
             except Exception as e:
                  agent_log.error(f"{self.name}: Error removing cyclic task {self.cyclic_task_id}: {e}")
        else:
             agent_log.debug(f"{self.name}: Cyclic task {self.cyclic_task_id} not found or manager unavailable during stop.")


        if self.processing_thread and self.processing_thread.is_alive():
            agent_log.info(f"{self.name}: Signaling message processing thread to stop.")
            self.message_queue.put(None)
            agent_log.info(f"{self.name}: Waiting for message processing thread to complete...")
            self.processing_thread.join(timeout=5.0)
            if self.processing_thread.is_alive():
                agent_log.warning(f"{self.name}: Message processing thread did not complete within timeout.")
            else:
                agent_log.info(f"{self.name}: Message processing thread finished.")
                self.processing_thread = None
        elif self.processing_thread:
             agent_log.info(f"{self.name}: Message processing thread already finished.")
             self.processing_thread = None


        self.task_threads = [t for t in self.task_threads if t != self.processing_thread and t.is_alive()]
        if self.task_threads:
            agent_log.info(f"{self.name}: Waiting for {len(self.task_threads)} active task threads to complete...")
            for thread in list(self.task_threads):
                thread.join(timeout=5.0)
                if thread.is_alive():
                    agent_log.warning(f"{self.name}: Task thread {thread.name} did not complete within timeout during stop.")
                else:
                    self.task_threads.remove(thread)
        else:
            agent_log.info(f"{self.name}: No other active task threads to wait for.")


        if self.broker:
            agent_log.info(f"{self.name}: Unsubscribing from topics: {self.subscriptions}")
            for topic in self.subscriptions:
                try:
                    self.broker.unsubscribe(topic, self.message_handler)
                except Exception as e:
                    agent_log.warning(f"{self.name}: Error unsubscribing from topic {topic}: {e}")
        else:
            agent_log.warning(f"{self.name}: Broker not available during stop, cannot unsubscribe.")

        self.broker = None
        self.cyclic_task_manager = None
        self.workflow_runtime = None

        agent_log.info(f"{self.name} stopped.")


    def _run_in_thread(self, target, args=()):
        """Helper to run a target function in a new thread with app context."""
        if not self.app_instance:
             agent_log.error(f"{self.name}: Cannot run in thread, Flask app instance is not set.")
             return threading.Thread()

        thread = run_thread_with_context(
            target=target,
            app=self.app_instance,
            args=args
        )
        return thread

    def _run_cyclic_task(self):
        """Executes the workflow's cyclic handler."""
        if not self.is_started:
            return

        self.task_threads = [t for t in self.task_threads if t.is_alive()]

        if self.workflow_runtime:
             try:
                  agent_log.debug(f"{self.name}: Running cyclic task via WorkflowRuntime.")
                  self.workflow_runtime.execute_cyclic()
             except Exception as e:
                 agent_log.exception(f"{self.name}: Error in cyclic handler execution via WorkflowRuntime: {e}")
        else:
              agent_log.error(f"{self.name}: WorkflowRuntime not available during cyclic task execution.")


    def _enqueue_message(self, topic: str, message: ACLMessage):
        """Callback for the message broker. Puts received messages onto the internal queue."""
        if self.is_started:
            self.message_queue.put((topic, message))
            agent_log.debug(f"{self.name}: Enqueued message for topic {topic}")
        else:
            agent_log.warning(f"{self.name}: Received message on topic {topic} while stopped. Discarding.")


    def _message_processing_loop(self):
        """Continuously processes messages from the internal queue in a dedicated thread."""
        agent_log.info(f"{self.name}: Message processing loop started.")
        while self.is_started:
            try:
                item = self.message_queue.get(block=True, timeout=1.0)

                if item is None:
                    agent_log.info(f"{self.name}: Received stop signal in processing loop.")
                    self.message_queue.task_done()
                    break

                topic, message = item
                if topic.startswith('/self'):
                    topic = topic.replace('/self', f'/agent:{self.id}')

                agent_log.debug(f"{self.name}: Dequeued message for topic {topic}. Processing...")

                if self.workflow_runtime:
                    self.workflow_runtime.execute_trigger(topic, message)
                else:
                    agent_log.error(f"{self.name}: WorkflowRuntime not available for handling trigger {topic}.")

                self.message_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                agent_log.exception(f"{self.name}: Unexpected error in message processing loop: {e}")
                time.sleep(0.1)

        agent_log.info(f"{self.name}: Message processing loop finished.")