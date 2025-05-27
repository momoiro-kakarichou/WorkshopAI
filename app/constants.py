class MessageRole:
    """
    Class for message roles
    """
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'
    TOOL = 'tool'
    NONE = 'none'
    
class StandartAgent:
    SYSTEM = 'SYSTEM'
    INTERFACE = 'INTERFACE'
    
class ACLPerformative:
    INFORM = 'inform'
    FAILURE = 'failure'
    CONFIRM = 'confirm'
    DISCONFIRM = 'disconfirm'
    ACCEPT = 'accept'
    DECLINE = 'decline'
    PROPOSAL = 'proposal'
    
# default broker topic
DEFAULT_TOPIC = '/default/topic'

CONFIG_PATH = "./config.json"

# paths
RESOURCES_PATH = './app/static/resources'
# CHARACTERS_PATH = RESOURCES_PATH + '/characters'
# LOREBOOKS_PATH = RESOURCES_PATH + '/lorebooks'
# PERSONAS_PATH = RESOURCES_PATH + '/personas'

DATA_PATH = './app/data'
CARDS_ASSETS_PATH = DATA_PATH + '/cards_assets'
PRESETS_PATH = DATA_PATH + '/presets'
# CHATS_PATH = DATA_PATH + '/chats'
# API_PATH = DATA_PATH + '/api'
# WORKFLOW_PATH = DATA_PATH + '/workflows'
# AGENTS_PATH = DATA_PATH + '/agents'

DATA_URL = 'data'
CARDS_ASSETS_URL = DATA_URL + '/cards_assets'
CARDS_ASSETS_ROUTE = '/cards_assets'

ASSETS_PATH = './app/assets'
TOKENIZERS_PATH = ASSETS_PATH + '/tokenizers'
API_CONFIGS_PATH = ASSETS_PATH + '/api'

# triggers
# USER_TRIGGER = 'user_message_send'
# SWIPE_TRIGGER = 'swipe_request'

CLAUDE3_MODEL_GROUP = 'claude3'
GPT4_MODEL_GROUP = 'gpt-4'