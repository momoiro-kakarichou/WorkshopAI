import logging
import coloredlogs
import json
import os
import functools
import threading
from flask import Flask
from typing import List, Any, Type
from functools import wraps

from app.extensions import log


def obj_to_json(obj: Any) -> str:
    """
    Converts an object to a JSON string.
    """
    return json.dumps(obj.to_dict())

def json_to_obj(json_str: str, obj_class: Type[Any] = None):
    """
    Converts a JSON string to an object of the specified class.
    """
    json_dict = json.loads(json_str)
    if obj_class:
        return obj_class(**json_dict)
    else:
        return json_dict

def save_json(json_str: str, file_path: str) -> None:
    """
    Saves a JSON string to a file.
    """
    try:
        with open(file_path, 'w') as file:
            file.write(json_str)
    except IOError as e:
        log.error(f"Error saving JSON to {file_path}: {e}")
        
def load_json(file_path: str) -> str:
    """
    Loads a JSON string from a file.
    """
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except IOError as e:
        log.error(f"Error loading JSON from {file_path}: {e}")
        return ""

def get_file_names(folder_path: str):
    """
    Retrieves the names of files in a specified folder.
    """
    if not os.path.exists(folder_path):
        log.error("Folder does not exist")
        return []

    return [item for item in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, item))]


def flatten(lst: List):
    """
    Flattens a nested list into a single list.
    """
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list

def insert_element(lst: List, index: int, element: Any):
    """
    Inserts an element into a list at the specified index.
    """
    if isinstance(lst[index], list):
        lst[index].append(element)
    else:
        lst[index] = [lst[index], element]
        
        
def process_joint_graph(serialized_graph):
    graph_data = json.loads(serialized_graph)

    cells = graph_data['cells']

    nodes = [cell for cell in cells if cell['type'] == 'standard.Rectangle']
    links = [cell for cell in cells if cell['type'] == 'standard.Link']

    # for node in nodes:
    #     node_id = node['id']
    #     position = node['position']
    #     size = node['size']
    #     label = node['attrs']['label']['text']

    # for link in links:
    #     link_id = link['id']
    #     source = link['source']['id']
    #     target = link['target']['id']
    
    return nodes, links

def exception_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(f"Error in {func.__name__}: {e}")
    return wrapper

def run_thread_with_context(target, app: Flask, args=(), kwargs=None):
    if kwargs is None:
        kwargs = {}

    def context_wrapper():
        with app.app_context():
            log.debug(f"App context pushed for thread '{threading.current_thread().name}' executing target '{target.__name__}'.")
            try:
                target(*args, **kwargs)
            except Exception:
                log.exception(f"Exception in thread '{threading.current_thread().name}' executing target '{target.__name__}'.")
            finally:
                 log.debug(f"App context will be popped for thread '{threading.current_thread().name}'.")

    thread = threading.Thread(target=context_wrapper, name=f"FlaskThread_{target.__name__}")
    thread.start()
    log.info(f"Started background thread '{thread.name}' for target '{target.__name__}'.")
    return thread

def flask_thread(app: Flask):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return run_thread_with_context(target=func, app=app, args=args, kwargs=kwargs)
        return wrapper
    return decorator

def create_logger(name: str, entity_name: str, level=logging.INFO):
    """Creates and configures a logger with colored output."""
    if level == logging.DEBUG:
        fmt=f'[%(asctime)s.%(msecs)03d][%(levelname)s][{entity_name}]: %(message)s'
    else:
        fmt=f'[%(asctime)s][%(levelname)s][{entity_name}]: %(message)s'
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        coloredlogs.install(level=level, logger=logger, fmt=fmt)
    return logger