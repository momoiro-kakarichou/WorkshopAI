import { socket, waitForEvent, AgentEvent, WorkflowEvent } from './socket.js';
import { AgentsContainerId, NewAgentDialog, AgentItem, NewAgentVarDialog, AgentVarItem } from './templates.js'
import { showModal, showConfirmationModal } from './common.js'

const module_prefix = '[AGENTS]:';
const AgentItemClass = '.agent-item'
const AgentVarItemClass = '.agent-var-item'

export function addAgentsHandlers() {
    $("#agents-list-sortable").sortable();
    $("#agents-list-sortable").disableSelection();

    $("#agent-variables-sortable").sortable();
    $("#agent-variables-sortable").disableSelection();

    cleanAgentEditor();

    // agents management

    function fetchWorkflowList(callback) {
        socket.emit(WorkflowEvent.WORKFLOW_LIST_REQUEST);
        waitForEvent(WorkflowEvent.WORKFLOW_LIST).then(data => {
            callback(data.workflows);
        });
    }

    function addAgent() {
        const selectedAgentId = $('#agents-selector').val();
        const selectedAgentName = $('#agents-selector option:selected').text();

        if (selectedAgentId && selectedAgentName) {
            const $list = $('#agents-list-sortable');
            const existingAgent = $list.find(`li[data-agent-id="${selectedAgentId}"]`);

            if (existingAgent.length === 0) {
                socket.emit(AgentEvent.AGENT_REQUEST, { id: selectedAgentId });
                waitForEvent(AgentEvent.AGENT).then(response => {
                    const is_started = response.is_started;
                    const $newItem = $(AgentItem(selectedAgentId, selectedAgentName));
                    if (is_started) {
                        $newItem.find('.agent-button-off').hide();
                    } else {
                        $newItem.find('.agent-button-on').hide();
                    }
                    $list.append($newItem);
                });
            }
        } else {
            toastr.warning("Please select an agent to add.");
        }
    }

    function newAgent() {
        showModal({ name: 'new-agent', title: 'New Agent', htmlContent: NewAgentDialog(), callback: () => {
            const agentName = $('#new-agent-name').val()
            const agentWorkflow = $('#new-agent-workflow').val()
            if (agentName) {
                const agentData = {
                    name: agentName,
                    workflow_id: agentWorkflow
                };
                socket.emit(AgentEvent.AGENT_SAVE_REQUEST, agentData);
                waitForEvent(AgentEvent.AGENT_SAVE).then(response => {
                    if (response.message === 'success') {
                        fetchAgentList();
                        const newAgentId = response.id;
                        $('#agents-selector').val(newAgentId).trigger('change');
                        toastr.success("Agent added");
                    } else {
                        toastr.error("Error adding agent: " + response.error);
                    }
                });
            }
        }});

        fetchWorkflowList((workflows) => {
            const $select = $('#new-agent-workflow');
            workflows.forEach(workflow => {
                $select.append($('<option>', { value: workflow.id, text: workflow.name }));
            });
        });
    }

    function deleteAgent() {
        const selectedAgent = $('#agents-selector').val();
        if (selectedAgent) {
            socket.emit(AgentEvent.AGENT_DELETE_REQUEST, { id: selectedAgent });
            waitForEvent(AgentEvent.AGENT_DELETE).then(response => {
                if (response.message === 'success') {
                    toastr.success("Agent deleted");
                    fetchAgentList();
                } else {
                    toastr.error("Error deleting agent: " + response.error);
                }
            });
        } else {
            toastr.warning("Please select a agent to delete.");
        }
    }

    function fetchAgentList() {
        const currentAgentId = $('#agents-selector').val();
    
        socket.emit(AgentEvent.AGENT_LIST_REQUEST);
        waitForEvent(AgentEvent.AGENT_LIST).then(data => {
            {
                updateAgentSelector(data.agents);
                if (currentAgentId && data.agents.some(wf => wf.id === currentAgentId)) {
                    $('#agents-selector').val(currentAgentId).trigger('change');
                } else {
                    const firstAgentId = data.agents[0].id;
                    $('#agents-selector').val(firstAgentId).trigger('change');
                }
            }
        });
    }

    function updateAgentSelector(agents) {
        const selector = $('#agents-selector');
        const currentAgentId = selector.val();
    
        selector.empty();
        for (const agent of agents) {
            selector.append(new Option(agent.name, agent.id));
        }
    
        if (currentAgentId && agents.some(wf => wf.id === currentAgentId)) {
            selector.val(currentAgentId);
        }
    }

    $('#agents-add-button').on('click', addAgent);
    $('#agents-new-button').on('click', newAgent);
    $('#agents-delete-button').on('click', deleteAgent);
    $('#agents-button').click(() => {
        if ($('#agents-menu-container').is(':visible')) {
            fetchAgentList();
        }
    });

    // agents list management

    let chosenAgentId = null;

    function cleanAgentEditor() {
        $('#agent-name').val('');
        $('#agent-version').empty().val(null);
        $('#agent-workflow').empty().val(null);
        $('#agent-description').val('');
        $('#agent-variables-sortable').empty();
    }

    function populateAgentEditor({name, version, version_list, workflow_id, workflow_list, description, vars_names}) {
        $('#agent-name').val(name);

        const $version = $('#agent-version');
        version_list.forEach(version => {
            $version.append(new Option(version, version));
        });
        $version.val(version);

        const $workflow = $('#agent-workflow');
        workflow_list.forEach(workflow => {
            $workflow.append(new Option(workflow.name, workflow.id));
        });
        $workflow.val(workflow_id);

        $('#agent-description').val(description);

        const $ul = $('#agent-variables-sortable');
        vars_names.forEach(item => {
            $ul.append(AgentVarItem(item));
        });
    }

    $(AgentsContainerId).on('click', '.agent-button-edit', function() {
        cleanAgentEditor()
        let agentItem = $(this).closest(AgentItemClass);
        let agentId = agentItem.data('agent-id');
        chosenAgentId = agentId;
        socket.emit(AgentEvent.AGENT_REQUEST, { id: agentId });
        waitForEvent(AgentEvent.AGENT).then(response => {
            let vars_names;
            if (response.vars) {
                vars_names = Object.keys(response.vars)
            } else {
                vars_names = []
            }
            fetchWorkflowList((workflow_list) => {
                populateAgentEditor({ name: response.name, version: response.version, version_list: response.versions_list, workflow_id: response.workflow_id,
                    workflow_list: workflow_list, description: response.description, vars_names: vars_names
                })
            });
        });
    });

    $(AgentsContainerId).on('click', '.agent-button-off', function() {
        const agentItem = $(this).closest(AgentItemClass);
        const agentId = agentItem.data('agent-id');
    
        socket.emit(AgentEvent.AGENT_START_REQUEST, { id: agentId });
        waitForEvent(AgentEvent.AGENT_START).then(response => {
            if (response.message === 'success') {
                toastr.success("Agent started successfully.");
                agentItem.find('.agent-button-off').hide();
                agentItem.find('.agent-button-on').show();
            } else {
                toastr.error("Error starting agent: " + response.error);
            }
        });
    });

    $(AgentsContainerId).on('click', '.agent-button-on', function() {
        const agentItem = $(this).closest(AgentItemClass);
        const agentId = agentItem.data('agent-id');
    
        socket.emit(AgentEvent.AGENT_STOP_REQUEST, { id: agentId });
        waitForEvent(AgentEvent.AGENT_STOP).then(response => {
            if (response.message === 'success') {
                toastr.success("Agent stopped successfully.");
                agentItem.find('.agent-button-on').hide();
                agentItem.find('.agent-button-off').show();
            } else {
                toastr.error("Error stopping agent: " + response.error);
            }
        });
    });

    function saveAgent() {
        if (chosenAgentId) {
            const agentData = {
                id: chosenAgentId,
                name: $('#agent-name').val(),
                version: $('#agent-version').val(),
                workflow_id: $('#agent-workflow').val(),
                description: $('#agent-description').val(),
            };
            socket.emit(AgentEvent.AGENT_SAVE_REQUEST, agentData);
            waitForEvent(AgentEvent.AGENT_SAVE).then(response => {
                if (response.message === 'success') {
                    toastr.success("Agent saved");
                } else {
                    toastr.error("Error saving agent: " + response.error);
                }
            });
        } else {
            toastr.warning('No agent is selected for saving.')
        }
    }

    $('#agents-save-button').on('click', saveAgent);

    // agents variables management

    function fetchAgentVariables() {
        if (chosenAgentId) {
            socket.emit(AgentEvent.AGENT_REQUEST, { id: chosenAgentId });
            waitForEvent(AgentEvent.AGENT).then(response => {
                if (response.vars) {
                    const $variablesList = $('#agent-variables-sortable');
                    $variablesList.empty();
    
                    Object.keys(response.vars).forEach(varName => {
                        $variablesList.append(AgentVarItem(varName));
                    });
                } else {
                    toastr.warning("No variables found for the selected agent.");
                }
            });
        } else {
            toastr.warning("No agent selected to fetch variables.");
        }
    }

    function addNewVariable() {
        showModal({
            name: 'new-agent-var',
            title: 'New Variable',
            htmlContent: NewAgentVarDialog(),
            callback: () => {
                const varName = $('#agent-var-name').val();
                const varType = $('#agent-var-type').val();

                if (varName && varType) {
                    socket.emit(AgentEvent.AGENT_NEW_VAR_REQUEST, {
                        id: chosenAgentId,
                        var_name: varName,
                        var_type: varType
                    });

                    waitForEvent(AgentEvent.AGENT_NEW_VAR).then(response => {
                        if (response.message === 'success') {
                            toastr.success("Variable added successfully.");
                            fetchAgentVariables();
                        } else {
                            toastr.error("Error adding variable: " + response.error);
                        }
                    });
                } else {
                    toastr.warning("Please provide both variable name and type.");
                }
            }
        });
    }

    function importVariables() {
        const fileInput = $('<input type="file" accept=".json">');
        fileInput.on('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    try {
                        const variables = JSON.parse(e.target.result);
                        if (chosenAgentId) {
                            socket.emit(AgentEvent.AGENT_IMPORT_VARS_REQUEST, {
                                id: chosenAgentId,
                                variables: variables
                            });

                            waitForEvent(AgentEvent.AGENT_IMPORT_VARS).then(response => {
                                if (response.message === 'success') {
                                    toastr.success("Variables imported successfully.");
                                    fetchAgentVariables();
                                } else {
                                    toastr.error("Error importing variables: " + response.error);
                                }
                            });
                        } else {
                            toastr.warning("No agent selected for importing variables.");
                        }
                    } catch (error) {
                        toastr.error("Invalid JSON file.");
                    }
                };
                reader.readAsText(file);
            }
        });
        fileInput.click();
    }

    function exportVariables() {
        if (chosenAgentId) {
            socket.emit(AgentEvent.AGENT_REQUEST, { id: chosenAgentId });
            waitForEvent(AgentEvent.AGENT).then(response => {
                if (response.vars) {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(response.vars, null, 2));
                    const downloadAnchor = $('<a>')
                        .attr('href', dataStr)
                        .attr('download', `${response.name}_variables.json`);
                    downloadAnchor[0].click();
                    toastr.success("Variables exported successfully.");
                } else {
                    toastr.warning("No variables found for the selected agent.");
                }
            });
        } else {
            toastr.warning("No agent selected for exporting variables.");
        }
    }

    $('#agents-variables-new-button').on('click', addNewVariable);
    $('#agents-variables-import-button').on('click', importVariables);
    $('#agents-variables-export-button').on('click', exportVariables);

    function editVariable(variableName, variableValue) {
        showModal({
            name: 'edit-agent-var',
            title: `Edit Variable: ${variableName}`,
            htmlContent: `
                <form>
                    <div class="form-group">
                        <label for="agent-var-value">Value:</label>
                        <textarea id="agent-var-value" class="form-control" rows="5">${variableValue}</textarea>
                    </div>
                </form>
            `,
            callback: () => {
                const newValue = $('#agent-var-value').val();
    
                if (chosenAgentId) {
                    const updatedVars = {};
                    updatedVars[variableName] = newValue;
    
                    socket.emit(AgentEvent.AGENT_IMPORT_VARS_REQUEST, {
                        id: chosenAgentId,
                        variables: updatedVars
                    });
    
                    waitForEvent(AgentEvent.AGENT_IMPORT_VARS).then(response => {
                        if (response.message === 'success') {
                            toastr.success("Variable updated successfully.");
                            fetchAgentVariables();
                        } else {
                            toastr.error("Error updating variable: " + response.error);
                        }
                    });
                } else {
                    toastr.warning("No agent selected for editing variables.");
                }
            }
        });
    }
    
    $(AgentsContainerId).on('click', '.agent-var-button-edit', function () {
        const variableItem = $(this).closest(AgentVarItemClass);
        const variableName = variableItem.find('.item-name').text();
    
        if (chosenAgentId) {
            socket.emit(AgentEvent.AGENT_REQUEST, { id: chosenAgentId });
            waitForEvent(AgentEvent.AGENT).then(response => {
                if (response.vars && response.vars[variableName] !== undefined) {
                    const variableValue = response.vars[variableName];
                    editVariable(variableName, JSON.stringify(variableValue, null, 2));
                } else {
                    toastr.warning("Variable not found.");
                }
            });
        } else {
            toastr.warning("No agent selected for editing variables.");
        }
    });

    function deleteVariable(variableName) {
        if (chosenAgentId) {
            socket.emit(AgentEvent.AGENT_DELETE_VAR_REQUEST, {
                id: chosenAgentId,
                var_name: variableName
            });
    
            waitForEvent(AgentEvent.AGENT_DELETE_VAR).then(response => {
                if (response.message === 'success') {
                    toastr.success("Variable deleted successfully.");
                    fetchAgentVariables();
                } else {
                    toastr.error("Error deleting variable: " + response.error);
                }
            });
        } else {
            toastr.warning("No agent selected for deleting variables.");
        }
    }
    
    $(AgentsContainerId).on('click', '.agent-var-button-delete', function () {
        const variableItem = $(this).closest(AgentVarItemClass);
        const variableName = variableItem.find('.item-name').text();
    
        showConfirmationModal({
            title: 'Delete Variable',
            message: `Are you sure you want to delete the variable "${variableName}"?`,
            onConfirm: () => {
                deleteVariable(variableName);
            }
        });
    });
}