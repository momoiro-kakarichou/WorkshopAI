import random
import hashlib
from datetime import datetime, timedelta, timezone
from enum import Enum

class ScopeEnum(Enum):
    PROMPT = 'prompt'
    DISPLAY = 'display'
    LOREBOOK = 'lorebook'

class MacroProcessor:
    def __init__(self, predefined_macros=None, max_depth=10):
        self.macros = predefined_macros if predefined_macros else {}
        self.max_depth = max_depth

    def add_macro(self, name, func):
        self.macros[name] = func

    def process(self, text, scope=ScopeEnum.PROMPT):
        return self._process_macros(text, scope, 0)

    def _process_macros(self, text, scope, depth):
        if depth > self.max_depth:
            return text

        result = ''
        i = 0
        while i < len(text):
            if text[i:i+2] == '{{':
                start = i
                i += 2
                stack = 1
                while i < len(text) and stack > 0:
                    if text[i:i+2] == '{{':
                        stack += 1
                        i += 2
                    elif text[i:i+2] == '}}':
                        stack -= 1
                        i += 2
                    else:
                        i += 1
                if stack == 0:
                    macro_content = text[start+2:i-2]
                    replacement = self._replace_macro(macro_content, text, scope, depth + 1)
                    if macro_content == 'trim':
                        result = result.rstrip()
                        while i < len(text) and text[i].isspace():
                            i += 1
                    else:
                        result += replacement
                else:
                    result += text[start:]
                    break
            else:
                result += text[i]
                i += 1
        return result

    def _replace_macro(self, macro_content, text, scope, depth):
        if depth > self.max_depth:
            return '{{' + macro_content + '}}'

        if ':' in macro_content:
            macro_name, macro_args = self._split_macro_content(macro_content)
            macro_args = self._process_macros(macro_args, scope, depth)
            if macro_name in self.macros:
                return self.macros[macro_name](macro_args=macro_args, original_text=text, scope=scope)
        elif macro_content.startswith('//'):
            macro_name = '//'
            return self.macros[macro_name]()
        else:
            macro_content = self._process_macros(macro_content, scope, depth)
            if macro_content in self.macros:
                return self.macros[macro_content]()
        return '{{' + macro_content + '}}'

    def _split_macro_content(self, content):
        stack = []
        for i, char in enumerate(content):
            if char == '{':
                stack.append(char)
            elif char == '}':
                stack.pop()
            elif char == ':' and not stack:
                return content[:i], content[i+1:]
        return content, ''


def random_macro(**kwargs):
    choices = kwargs['macro_args'].split(',')
    return random.choice(choices)

#zaglushka
def pick_macro(**kwargs):
    choices = kwargs['macro_args'].split(',')
    seed = int(hashlib.md5(kwargs['original_text'].encode()).hexdigest(), 16)
    random.seed(seed)
    return random.choice(choices)

def roll_macro(**kwargs):
    try:
        n = int(kwargs['macro_args'])
        return str(random.randint(1, n))
    except ValueError:
        return '{{roll:' + kwargs['macro_args'] + '}}'
    
def reverse_macro(**kwargs):
    return kwargs['macro_args'][::-1]

def comment_macro(**kwargs):
    if kwargs['scope'] == ScopeEnum.DISPLAY:
        return kwargs['macro_args']
    else:
        return ''

def hidden_key_macro(**kwargs):
    if kwargs['scope'] == ScopeEnum.LOREBOOK:
        return kwargs['macro_args']
    else:
        return ''
    
def hidden_prompt_macro(**kwargs):
    if kwargs['scope'] == ScopeEnum.PROMPT:
        return kwargs['macro_args']
    else:
        return ''
    
def time_macro(**kwargs):
    return datetime.now().strftime('%H:%M:%S')

def date_macro(**kwargs):
    return datetime.now().strftime('%Y-%m-%d')

def weekday_macro(**kwargs):
    return datetime.now().strftime('%A')

def isotime_macro(**kwargs):
    return datetime.now().isoformat(timespec='seconds')

def isodate_macro(**kwargs):
    return datetime.now().date().isoformat()

def datetimeformat_macro(**kwargs):
    format_str = kwargs['macro_args']
    return datetime.now().strftime(format_str)

def time_UTC_macro(**kwargs):
    offset = int(kwargs['macro_args'])
    utc_time = datetime.now(timezone.utc) + timedelta(hours=offset)
    return utc_time.strftime('%H:%M:%S')

def timeDiff_macro(**kwargs):
    time1_str, time2_str = kwargs['macro_args'].split('::')
    time1 = datetime.fromisoformat(time1_str)
    time2 = datetime.fromisoformat(time2_str)
    diff = abs(time1 - time2)
    return str(diff)

# change placeholders
predefined_macros = {
    'char': lambda: 'char placeholder',
    'user': lambda: 'user placeholder',
    'random': random_macro,
    'pick': pick_macro,
    'roll': roll_macro,
    'reverse': reverse_macro,
    '//': lambda: '',
    'comment': comment_macro,
    'hidden_key': hidden_key_macro,
    'hidden_prompt': hidden_prompt_macro,
    'newline': lambda: '\n',
    'trim': lambda: '',
    'time': time_macro,
    'date': date_macro,
    'weekday': weekday_macro,
    'isotime': isotime_macro,
    'isodate': isodate_macro,
    'datetimeformat': datetimeformat_macro,
    'time_UTC': time_UTC_macro,
    'timeDiff': timeDiff_macro
}

macroProcessor = MacroProcessor(predefined_macros)
# text = "char: {{char}}, user: {{user}}, Random: {{random:{{char}},{{user}}}}, Comment: {{// This is a comment}}, also comment: {{comment: the comment}} Reverse: {{reverse:Hello}}, Pick: {{pick:A,B,C,D,E,F,G}}, Unknown: {{unknown}}, Time: {{time}}, Date: {{date}}, Weekday: {{weekday}}, ISO Time: {{isotime}}, ISO Date: {{isodate}}, DateTime Format: {{datetimeformat:%d.%m.%Y %H:%M}}, Time UTC: {{time_UTC:+2}}, Time Diff: {{timeDiff:2023-10-01T12:00:00::2023-10-01T15:00:00}}, Trim: \n{{trim}} \n\t  here"
# processed_text = macroProcessor.process(text)
# print(processed_text)

# text = "{{random:{{random:{{random:{{random:{{random:{{random:{{char}},{{user}}}}}}}}}}}}}}"
# processed_text = macroProcessor.process(text)
# print(processed_text)