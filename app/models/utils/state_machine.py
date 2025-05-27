class StateMachine:
    def __init__(self, states, states_content, initial_state):
        self.states = states
        self.states_content = states_content
        self.current_state = initial_state
        
    def add_state(self, state_name, state_content):
        self.states_content[state_name] = state_content
        if state_name not in self.states:
            self.states[state_name] = {}
        else:
            raise ValueError(f"State '{state_name}' already exists")

    def add_transition(self, from_state, event, to_state):
        if from_state not in self.states:
            raise ValueError(f"State '{from_state}' does not exist")
        if to_state not in self.states:
            raise ValueError(f"State '{to_state}' does not exist")
        self.states[from_state][event] = to_state

    def transition(self, event):
        if event in self.states[self.current_state]:
            self.current_state = self.states[self.current_state][event]
        else:
            raise ValueError(f"No transition for event '{event}' in state '{self.current_state}'")

    def get_state(self) -> str:
        return self.current_state
    
    def get_state_content(self) -> str:
        return self.states_content[self.current_state]