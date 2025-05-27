import io

from tokenizers import Tokenizer
from tiktoken import encoding_for_model

from app.extensions import log
from app.constants import CLAUDE3_MODEL_GROUP, TOKENIZERS_PATH, GPT4_MODEL_GROUP


def get_tokenizer(model_group: str) -> Tokenizer:
    """
    Retrieves the tokenizer for the specified model group.
    """
    if model_group == CLAUDE3_MODEL_GROUP:
        try:
            with io.open(f'{TOKENIZERS_PATH}/{model_group}_tokenizer.json', mode="r", encoding="utf-8") as f:
                tokenizer_raw = f.read()
                return Tokenizer.from_str(tokenizer_raw)
        except IOError as e:
            log.error(f"Error loading tokenizer for {model_group}: {e}")
            return None
    elif GPT4_MODEL_GROUP in model_group:
        return encoding_for_model(model_group)
    else:
        log.error(f"Unknown model group: {model_group}")
        return None

def count_tokens(model_group: str, text: str):
    """
    Counts the number of tokens in a text for the specified model group.
    """
    if model_group == CLAUDE3_MODEL_GROUP:
        tokenizer = claude3_tokenizer
    elif model_group == GPT4_MODEL_GROUP:
        tokenizer = gpt4_tokenizer
    else:
        log.error(f"Unknown model group: {model_group}")
        return 0

    encoded_text = tokenizer.encode(text)
    return len(encoded_text.ids)


claude3_tokenizer = get_tokenizer(CLAUDE3_MODEL_GROUP)
gpt4_tokenizer = get_tokenizer(GPT4_MODEL_GROUP)