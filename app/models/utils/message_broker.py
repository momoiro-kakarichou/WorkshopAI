import threading
from typing import Callable, Dict, List, Optional
from app.models.utils.acl_message import ACLMessage
from app.utils.utils import create_logger
from app.context import context

message_broker_log = create_logger(__name__, entity_name='MESSAGE_BROKER', level=context.log_level)

class Waiter:
    def __init__(self, filter_func: Optional[Callable[[ACLMessage], bool]] = None):
        self.filter_func = filter_func
        self.event = threading.Event()
        self.message: Optional[ACLMessage] = None

class MessageBroker:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[str, ACLMessage], None]]] = {}

    def subscribe(self, topic: str, subscriber: Callable[[str, ACLMessage], None]):
        if topic in self.subscribers and subscriber in self.subscribers[topic]:
            message_broker_log.info(f"Subscriber {subscriber} already subscribed to exact topic {topic}. Ignoring.")
            return

        is_covered = False
        for existing_topic, subscribers_list in list(self.subscribers.items()):
            if subscriber in subscribers_list and self._is_wildcard(existing_topic) and self._matches(existing_topic, topic):
                message_broker_log.info(f"Subscriber {subscriber} subscription to {topic} is already covered by existing wildcard topic {existing_topic}. Ignoring.")
                is_covered = True
                break
        if is_covered:
            return

        topics_to_remove = []
        if self._is_wildcard(topic):
            for existing_topic, subscribers_list in list(self.subscribers.items()):
                if subscriber in subscribers_list and not self._is_wildcard(existing_topic) and self._matches(topic, existing_topic):
                    topics_to_remove.append(existing_topic)
                    message_broker_log.info(f"New wildcard subscription {topic} for {subscriber} overrides existing specific subscription {existing_topic}. Removing specific.")

            for t_remove in topics_to_remove:
                if t_remove in self.subscribers and subscriber in self.subscribers[t_remove]:
                    self.subscribers[t_remove].remove(subscriber)
                    message_broker_log.info(f"Removed subscriber {subscriber} from specific topic {t_remove} due to overriding wildcard {topic}")
                    if not self.subscribers[t_remove]:
                        del self.subscribers[t_remove]
                        message_broker_log.info(f"Removed empty topic {t_remove} from subscriptions.")


        if topic not in self.subscribers:
            self.subscribers[topic] = []
        if subscriber not in self.subscribers[topic]:
            self.subscribers[topic].append(subscriber)
            message_broker_log.info(f"Subscriber {subscriber} subscribed to topic {topic}")

    def unsubscribe(self, topic: str, subscriber: Callable[[str, ACLMessage], None]):
        if topic in self.subscribers:
            if subscriber in self.subscribers[topic]:
                self.subscribers[topic].remove(subscriber)
                message_broker_log.info(f"Subscriber {subscriber} unsubscribed from topic {topic}")
            if not self.subscribers[topic]:
                del self.subscribers[topic]


    def publish(self, topic: str, message: ACLMessage):
        message_broker_log.info(f"Publishing message to topic {topic}: {message}")
        for subscribed_topic, subscribers in list(self.subscribers.items()):
            if self._matches(subscribed_topic, topic):
                for subscriber in subscribers:
                    self._dispatch_message(subscriber, topic, message)

    def _dispatch_message(self, subscriber: Callable[[str, ACLMessage], None], topic: str, message: ACLMessage):
        try:
            subscriber(topic, message)
        except Exception as e:
            message_broker_log.error(f"Error dispatching message to {subscriber} on topic {topic}: {e}")

    def _matches(self, subscribed_topic: str, published_topic: str) -> bool:
        """Checks if a published topic matches a subscribed topic"""
        if subscribed_topic == published_topic:
            return True

        if not self._is_wildcard(subscribed_topic):
            return False

        sub_parts = subscribed_topic.split('/')
        pub_parts = published_topic.split('/')

        sub_len = len(sub_parts)
        pub_len = len(pub_parts)

        i = 0
        while i < sub_len and i < pub_len:
            sub_part = sub_parts[i]
            pub_part = pub_parts[i]

            if sub_part == '#':
                return i == sub_len - 1

            if sub_part != '+' and sub_part != pub_part:
                return False

            i += 1

        if i == sub_len and i == pub_len:
            return True

        if i == pub_len and sub_len == i + 1 and sub_parts[i] == '#':
            return True

        return False
    
    def _is_wildcard(self, topic: str) -> bool:
        """Checks if a topic string contains wildcards '+' or '#'."""
        return '+' in topic or '#' in topic

    
    def subscribe_once(self, topic: str, filter_func: Optional[Callable[[ACLMessage], bool]] = None) -> Waiter:
        waiter = Waiter(filter_func)

        def once_handler(received_topic: str, message: ACLMessage):
            if waiter.filter_func is None or waiter.filter_func(message):
                waiter.message = message
                waiter.event.set()
                self.unsubscribe(topic, once_handler)

        self.subscribe(topic, once_handler)
        return waiter
    
    def wait_for_message(self, waiter: Waiter, timeout:float):
        if waiter.event.wait(timeout):
            return waiter.message
        else:
            raise TimeoutError("Timeout waiting for message")