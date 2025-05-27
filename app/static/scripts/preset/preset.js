import { socket, waitForEvent, WorkflowEvent } from '../socket.js';
import { initCustomShapes, updateNoteText, getNode, getLink, getWindow, getNote, adjustZIndex, isNodeInsideWindow, setInterfaceHTML, toggleNodeInterface } from './shapes.js';
import { createCodeEditor } from '../format.js'
import { AddNodeDialog, SelectOption } from '../templates.js'
import { showNameDialog, showModal } from '../common.js'

const module_prefix = '[BOARD]:';

export function addPresetHandlers() {
    initCustomShapes();

    const graph = new joint.dia.Graph();

    const paper = new joint.dia.Paper({
        el: $('.paper-container'),
        model: graph,
        width: '100%',
        height: '100%',
        gridSize: 10,
        drawGrid: true,
        interactive: { linkMove: false }
    });

    // Workflow management

    function addWorkflow() {
        showNameDialog((workflowName) => {
            if (workflowName) {
                const workflowData = {
                    name: workflowName,
                    graph: { cells: [] }
                };
                socket.emit(WorkflowEvent.WORKFLOW_SAVE_REQUEST, workflowData);
                waitForEvent(WorkflowEvent.WORKFLOW_SAVE).then(response => {
                    if (response.message === 'success') {
                        fetchWorkflowList();
                        const newWorkflowId = response.id;
                        $('#workflow-selector').val(newWorkflowId).trigger('change');
                        toastr.success("Workflow added");
                    } else {
                        toastr.error("Error adding workflow: " + response.error);
                    }
                });
            }
        });
    }

    function saveWorkflow() {
        const selectedWorkflow = $('#workflow-selector').val();
        if (selectedWorkflow) {
            const workflowData = {
                id: selectedWorkflow,
                graph: graph.toJSON()
            };
            socket.emit(WorkflowEvent.WORKFLOW_SAVE_REQUEST, workflowData);
            waitForEvent(WorkflowEvent.WORKFLOW_SAVE).then(response => {
                if (response.message === 'success') {
                    toastr.success("Workflow saved");
                } else {
                    toastr.error("Error saving workflow: " + response.error);
                }
            });
        } else {
            toastr.warning("Please select a workflow to save.");
        }
    }

    function deleteWorkflow() {
        const selectedWorkflow = $('#workflow-selector').val();
        if (selectedWorkflow) {
            socket.emit(WorkflowEvent.WORKFLOW_DELETE_REQUEST, { id: selectedWorkflow });
            waitForEvent(WorkflowEvent.WORKFLOW_DELETE).then(response => {
                if (response.message === 'success') {
                    toastr.success("Workflow deleted");
                    fetchWorkflowList();
                } else {
                    toastr.error("Error deleting workflow: " + response.error);
                }
            });
        } else {
            toastr.warning("Please select a workflow to delete.");
        }
    }

    function fetchWorkflowList() {
        const currentWorkflowId = $('#workflow-selector').val();
    
        socket.emit(WorkflowEvent.WORKFLOW_LIST_REQUEST);
        waitForEvent(WorkflowEvent.WORKFLOW_LIST).then(data => {
            if (data.workflows.length === 0) {
                saveEmptyWorkflow();
            } else {
                updateWorkflowSelector(data.workflows);
                if (currentWorkflowId && data.workflows.some(wf => wf.id === currentWorkflowId)) {
                    $('#workflow-selector').val(currentWorkflowId).trigger('change');
                } else {
                    const firstWorkflowId = data.workflows[0].id;
                    $('#workflow-selector').val(firstWorkflowId).trigger('change');
                }
            }
        });
    }

    function fetchWorkflowData(workflowId) {
        socket.emit(WorkflowEvent.WORKFLOW_REQUEST, { id: workflowId });
        waitForEvent(WorkflowEvent.WORKFLOW).then(data => {
            graph.fromJSON(data.graph);
            graph.getElements().forEach(element => {
                if (element instanceof joint.shapes.custom.NodeWithButton) {
                    const fillColor = element.attr('body/fill');
                    if (fillColor !== 'lightgray' && fillColor !== 'lightgreen') {
                        element.attr('pencilButton/display', 'none');
                        element.attr('pencilButtonOverlay/display', 'none');
                    } else {
                        element.attr('pencilButton/display', 'block');
                        element.attr('pencilButtonOverlay/display', 'block');
                    }
                }
            });
            data.links.forEach(link => {
                const sourceNode = graph.getElements().find(el => el.get('customId') === link.source);
                const targetNode = graph.getElements().find(el => el.get('customId') === link.target);
                if (sourceNode && targetNode) {
                    const newLink = getLink(graph, sourceNode, targetNode);
                    if (newLink) {
                        newLink.addTo(graph);
                    }
                }
            });
        });
    }

    function saveEmptyWorkflow() {
        const workflowName = 'Default';
        if (workflowName) {
            const workflowData = {
                name: workflowName,
                graph: { cells: [] }
            };
            socket.emit(WorkflowEvent.WORKFLOW_SAVE_REQUEST, workflowData);
            waitForEvent(WorkflowEvent.WORKFLOW_SAVE).then(response => {
                if (response.message === 'success') {
                    fetchWorkflowList();
                } else {
                    toastr.error("Error saving workflow: " + response.error);
                }
            });
        }
    }

    function updateWorkflowSelector(workflows) {
        const selector = $('#workflow-selector');
        const currentWorkflowId = selector.val();
    
        selector.empty();
        for (const workflow of workflows) {
            selector.append(new Option(workflow.name, workflow.id));
        }
    
        if (currentWorkflowId && workflows.some(wf => wf.id === currentWorkflowId)) {
            selector.val(currentWorkflowId);
        }
    }

    $('#workflow-selector').on('change', function() {
        const selectedWorkflow = $(this).val();
        if (selectedWorkflow) {
            fetchWorkflowData(selectedWorkflow);
        }
    });

    $('#add-workflow-button').on('click', addWorkflow);
    $('#save-workflow-button').on('click', saveWorkflow);
    $('#delete-workflow-button').on('click', deleteWorkflow);
    $('#preset-button').click(() => {
        if ($('#preset-menu-container').is(':visible')) {
            fetchWorkflowList();
        }
    });

    // Node management

    function saveNode({ node, node_type, node_subtype, handler, is_new_node = false, workflow_id, name, interfaceData, code, static_input }) { // Added static_input
        const workflowId = workflow_id || $('#workflow-selector').val();
        if (workflowId) {
            const nodeData = {
                workflow_id: workflowId,
                name: name,
                ...(interfaceData && { interface: interfaceData }),
                ...(node_type && { node_type: node_type }),
                ...(node_subtype && { node_subtype: node_subtype }),
                ...(handler && { handler: handler }),
                ...(code && { code: code }),
                ...(static_input && { static_input: static_input }),
                ...(!is_new_node && { id: node.get('customId') })
            };
    
            socket.emit(WorkflowEvent.NODE_SAVE_REQUEST, nodeData);
            waitForEvent(WorkflowEvent.NODE_SAVE).then(response => {
                if (response.message === 'success') {
                    if (is_new_node) {
                        node.set('customId', response.id);
                        graph.addCell(node);
                        saveWorkflow();
                    }
                    toastr.success("Node saved");
                } else {
                    toastr.error("Error saving node: " + response.error);
                }
            });
        } else {
            toastr.warning("Please select a workflow to save the node.");
        }
    }

    function deleteNode(nodeId) {
        const workflowId = $('#workflow-selector').val();
        if (workflowId) {
            socket.emit(WorkflowEvent.NODE_DELETE_REQUEST, { workflow_id: workflowId, id: nodeId });
            waitForEvent(WorkflowEvent.NODE_DELETE).then(response => {
                if (response.message === 'success') {
                    toastr.success("Node deleted");
                } else {
                    toastr.error("Error deleting node: " + response.error);
                }
            });
        } else {
            toastr.warning("Please select a workflow to delete the node.");
        }
    }

    function fetchNodeData(nodeId, callback) {
        const workflowId = $('#workflow-selector').val();
        if (workflowId) {
            socket.emit(WorkflowEvent.NODE_CONTENT_REQUEST, { workflow_id: workflowId, id: nodeId });
            waitForEvent(WorkflowEvent.NODE_CONTENT).then(data => {
                const node = graph.getElements().find(el => el.get('customId') === nodeId);
                if (node) {
                    if (callback) {
                        callback(node, data);
                    }
                }
            });
        } else {
            toastr.warning("Please select a workflow to fetch the node data.");
        }
    }

    function generateFormField(key, definition) {
        const id = `node-interface-${key}`;
        let fieldHtml = `<div class="form-group">
                           <label class="fw-bold" for="${id}">${definition.label || key}</label>`;
    
        switch (definition.type) {
            case 'text':
                fieldHtml += `<input type="text" class="form-control" id="${id}" name="${key}" placeholder="${definition.placeholder || ''}" value="${definition.default || ''}">`;
                break;
            case 'textarea':
                fieldHtml += `<textarea class="form-control" id="${id}" name="${key}" rows="${definition.rows || 3}" placeholder="${definition.placeholder || ''}">${definition.default || ''}</textarea>`;
                break;
            case 'number':
                fieldHtml += `<input type="number" class="form-control" id="${id}" name="${key}" value="${definition.default || 0}" step="${definition.step || 'any'}">`;
                break;
            case 'checkbox':
                fieldHtml += `<div class="form-check"><input type="checkbox" class="form-check-input" id="${id}" name="${key}" ${definition.default ? 'checked' : ''}><label class="form-check-label" for="${id}"></label></div>`;
                break;
            case 'select':
                fieldHtml += `<select class="form-control" id="${id}" name="${key}" ${definition.options_source ? `data-options-source="${definition.options_source}"` : ''}>`;
                if (definition.options_source) {
                    fieldHtml += `<option value="">Loading...</option>`;
                } else {
                    (definition.options || []).forEach(option => {
                        const value = typeof option === 'object' ? option.value : option;
                        const text = typeof option === 'object' ? option.text : option;
                        fieldHtml += `<option value="${value}" ${value == definition.default ? 'selected' : ''}>${text}</option>`;
                    });
                }
                fieldHtml += `</select>`;
                break;
            default:
                fieldHtml += `<input type="text" class="form-control" id="${id}" name="${key}" placeholder="Unsupported type: ${definition.type}" value="${definition.default || ''}">`;
        }
    
        if (definition.description) {
            fieldHtml += `<small>${definition.description}</small>`;
        }
    
        fieldHtml += `</div>`;
        return fieldHtml;
    }
    
    
    function initializeNodeInterfaceSelects_Embedded(nodeElement, workflowId, nodeId, staticInputData) {
        const nodeView = paper.findViewByModel(nodeElement);
        if (!nodeView) {
            console.warn("Node view not found for initializing selects.");
            return;
        }

        const foSVGElement = nodeView.el.querySelector('foreignObject[joint-selector="interfaceForm"]');
        if (!foSVGElement) {
            console.warn("ForeignObject for interfaceForm not found in node view. Node ID:", nodeId);
            return;
        }

        const foDiv = foSVGElement.firstChild;
        if (!foDiv) {
            console.warn("Content div inside foreignObject not found.");
            return;
        }

        $(foDiv).find('select').each(function() {
            const $select = $(this);
            const optionsSource = $select.data('options-source');
            const fieldKey = $select.attr('name');

            if (!optionsSource) {
                if (!$select.data('select2')) {
                    $select.select2({
                        dropdownParent: $(foDiv),
                        width: '100%'
                    });
                    if (staticInputData.hasOwnProperty(fieldKey)) {
                        $select.val(staticInputData[fieldKey]).trigger('change');
                    }
                }
                return;
            }

            if (workflowId && nodeId) {
                $select.empty().append('<option value="">Loading...</option>');
                socket.emit(WorkflowEvent.NODE_GET_DYNAMIC_OPTIONS_REQUEST, {
                    workflow_id: workflowId,
                    node_id: nodeId,
                    options_source: optionsSource
                });

                waitForEvent(WorkflowEvent.NODE_GET_DYNAMIC_OPTIONS).then(response => {
                    if (response.message === 'success' && response.options_source === optionsSource) {
                        $select.empty();
                        response.options.forEach(option => {
                            const value = typeof option === 'object' ? option.value : option;
                            const text = typeof option === 'object' ? option.text : option;
                            $select.append(new Option(text, value));
                        });

                        if (staticInputData.hasOwnProperty(fieldKey)) {
                            $select.val(staticInputData[fieldKey]);
                        }

                        if (!$select.data('select2')) {
                            $select.select2({
                                dropdownParent: $(foDiv),
                                width: '100%'
                            });
                        } else {
                            $select.trigger('change.select2');
                        }
                    } else {
                        toastr.error(`Error loading options for ${optionsSource}: ${response.error || 'Unknown error'}`);
                        $select.empty().append('<option value="">Error loading</option>');
                    }
                }).catch(error => {
                    console.error(`Error fetching dynamic options for ${optionsSource}:`, error);
                    toastr.error(`Timeout or error loading options for ${optionsSource}`);
                    $select.empty().append('<option value="">Error loading</option>');
                });
            } else {
                toastr.warning("Workflow or Node ID missing, cannot load dynamic options.");
                $select.empty().append('<option value="">Error loading</option>');
            }
        });
    }

    function saveNodeInterface_Embedded(node, nodeData, interfaceData) {
        const nodeId = node.get('customId');
        const nodeView = paper.findViewByModel(node);
        if (!nodeView) {
            console.error("Node view not found for saving interface:", nodeId);
            toastr.error("Could not save: Node view not found.");
            return;
        }

        const foSVGElement = nodeView.el.querySelector('foreignObject[joint-selector="interfaceForm"]');
        if (!foSVGElement || !foSVGElement.firstChild) {
            console.error("ForeignObject or its content not found for saving:", nodeId);
            toastr.error("Could not save: Interface container not found.");
            return;
        }
        const foDiv = foSVGElement.firstChild;
        const formId = `node-interface-form-${nodeId}`;
        const formElement = foDiv.querySelector(`#${formId}`);

        if (!formElement) {
            console.error("Embedded node interface form not found:", formId, "within", foDiv);
            toastr.error("Could not save: Interface form not found.");
            return;
        }

        const formData = new FormData(formElement);
        const newStaticInput = {};
        const originalStaticInput = nodeData.static_input || {};

        for (const key in interfaceData) {
            if (interfaceData.hasOwnProperty(key)) {
                const definition = interfaceData[key];
                if (definition.type === 'checkbox') {
                    newStaticInput[key] = formData.has(key);
                } else if (formData.has(key)) {
                    newStaticInput[key] = formData.get(key);
                } else {
                    newStaticInput[key] = originalStaticInput.hasOwnProperty(key) ? originalStaticInput[key] : (definition.default !== undefined ? definition.default : null);
                }
            }
        }
        console.log("Saving new static input (embedded):", newStaticInput);

        saveNode({
            node: node,
            name: nodeData.name,
            static_input: newStaticInput
        });
    }


    function generateNodeInterfaceHTMLString(theNode, nodeData) {
        const interfaceData = nodeData.interface || {};
        const staticInputData = nodeData.static_input || {};
        const nodeId = theNode.get('customId');
        const formId = `node-interface-form-${nodeId}`;

        let formHtml = `<form id="${formId}" class="node-interface-form-embedded" style="padding: 10px;">`;

        for (const key in interfaceData) {
            if (interfaceData.hasOwnProperty(key)) {
                let definition = JSON.parse(JSON.stringify(interfaceData[key]));
                definition.default = staticInputData.hasOwnProperty(key) ? staticInputData[key] : definition.default;
                formHtml += generateFormField(key, definition); // generateFormField should produce HTML string
            }
        }
        
        if (Object.keys(interfaceData).length === 0) {
            formHtml += '<p>This node has no configurable interface.</p>';
        }

        formHtml += `<button type="button" class="btn btn-primary btn-sm" onclick="handleSaveEmbeddedInterface('${nodeId}')" style="margin-top: 10px;">Save</button>`;
        formHtml += '</form>';

        return formHtml;
    }

    if (!window.handleSaveEmbeddedInterface) {
        window.handleSaveEmbeddedInterface = function(nodeId) {
            const node = graph.getElements().find(el => el.get('customId') === nodeId);
            if (node) {
                fetchNodeData(nodeId, (fetchedNode, data) => {
                    if (data && !data.error && data.interface) {
                        saveNodeInterface_Embedded(fetchedNode, data, data.interface);
                    } else if (data && !data.error && !data.interface) {
                        saveNodeInterface_Embedded(fetchedNode, data, {});
                    }
                    else {
                        toastr.error(`Error fetching node data for save: ${data?.error || 'Node data or interface definition missing'}`);
                    }
                });
            } else {
                toastr.error("Node not found for saving interface.");
            }
        };
    }


    function renderNodeInterface(node, nodeData) {
        const nodeId = node.get('customId') || node.id;
        console.log(`[preset.js] renderNodeInterface called for node: ${nodeId}`);
        if (nodeData && !nodeData.error) {
            const htmlString = generateNodeInterfaceHTMLString(node, nodeData);
            console.log(`[preset.js] HTML string generated for ${nodeId}:`, String(htmlString).substring(0,100));
            setInterfaceHTML(node, htmlString); // from shapes.js
            console.log(`[preset.js] setInterfaceHTML called for ${nodeId}`);
            console.log(`[preset.js] Node model attr 'interfaceForm/html' (first 100 chars):`, String(node.attr('interfaceForm/html')).substring(0,100));
            
            const elementView = paper.findViewByModel(node);
            if (elementView) {
                const foSVGElement = elementView.el.querySelector('foreignObject[joint-selector="interfaceForm"]');
                if (foSVGElement && foSVGElement.firstChild) {
                    const foDiv = foSVGElement.firstChild;
                    const contentScrollHeight = foDiv.scrollHeight;
                    const headerHeight = 20;
                    const padding = 20;
                    const newExpandedHeight = contentScrollHeight + headerHeight + padding;
                    const currentExpandedWidth = node.get('expandedSize').width;

                    console.log(`[preset.js] Calculated newExpandedHeight for ${nodeId}: ${newExpandedHeight} (scrollHeight: ${contentScrollHeight})`);
                    
                    node.set('expandedSize', { width: currentExpandedWidth, height: newExpandedHeight });
                    node.resize(currentExpandedWidth, newExpandedHeight);
                    
                    node.attr('interfaceForm/height', newExpandedHeight - headerHeight);

                    console.log(`[preset.js] Node ${nodeId} resized to: ${currentExpandedWidth}x${newExpandedHeight}`);
                } else {
                    console.warn(`[preset.js] Could not find foreignObject or its child to calculate scrollHeight for ${nodeId}.`);
                }

                console.log(`[preset.js] Forcing render for view of node ${nodeId} after potential resize and setting HTML.`);
                elementView.render();
                
                if (foSVGElement) {
                    const foRect = foSVGElement.getBoundingClientRect();
                    console.log(`[preset.js] foreignObject DOM rect for ${nodeId} AFTER resize:`, { width: foRect.width, height: foRect.height, top: foRect.top, left: foRect.left });
                }

            } else {
                console.warn(`[preset.js] ElementView not found for node ${nodeId} after setting HTML.`);
            }

            const workflowId = $('#workflow-selector').val();
            initializeNodeInterfaceSelects_Embedded(node, workflowId, nodeId, nodeData.static_input || {});
            console.log(`[preset.js] initializeNodeInterfaceSelects_Embedded called for ${nodeId}`);
        } else {
            toastr.error(`Error fetching node data for rendering: ${nodeData?.error || 'Unknown error'}`);
            setInterfaceHTML(node, "<p>Error loading interface.</p>");
            const elementView = paper.findViewByModel(node);
            if (elementView) elementView.render();
        }
        console.log(`[preset.js] renderNodeInterface finished for node: ${nodeId}`);
    }

    // Node event listeners

    paper.on('element:eyeButton:pointerdown', function(elementView, evt) {
        evt.stopPropagation();
        const node = elementView.model;
        const nodeId = node.get('customId');

        toggleNodeInterface(node, paper);

        if (node.get('interfaceVisible')) {
            if (nodeId) {
                fetchNodeData(nodeId, (fetchedNode, nodeData) => {
                    renderNodeInterface(fetchedNode, nodeData);
                });
            } else {
                toastr.warning("Node has no ID yet. Cannot display interface.");
                setInterfaceHTML(node, "<p>Node not saved. Cannot display interface.</p>");
            }
        }
    });

    paper.on('element:pencilButton:pointerdown', function(elementView, evt) {
        evt.stopPropagation();
        openCodeEditor(elementView);
    });

    paper.on('element:ledButton:pointerdown', function(elementView, evt) {
        evt.stopPropagation();
        const paleRedColor = '#DB2B2B';
        const led = elementView.model.attr('ledButton/fill');
        const newColor = led === paleRedColor ? 'green' : paleRedColor;
        elementView.model.attr('ledButton/fill', newColor);
    });

    $('#board-delete-node').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.shapes.custom.NodeWithButton) {
            const nodeId = selectedElement.get('customId');
            selectedElement.remove();
            deleteNode(nodeId);
        }
        contextMenu.hide();
    });

    $('#board-add-node').click(function() {
        const dialogHtml = AddNodeDialog();
        showModal({
            name: 'add-node-dialog',
            title: 'Add Node',
            htmlContent: dialogHtml,
            callback: function() {
                const name = $('#add-node-name').val();
                const type = $('#add-node-type').val();
                const subtype = $('#add-node-subtype').val();
    
                if (!name || !type) {
                    toastr.warning('Please provide a name and type for the node.');
                    return;
                }
    
                const node = getNode(paper, name);
    
                let fillColor;
                switch (type) {
                    case 'trigger':
                        fillColor = 'lightgreen';
                        break;
                    case 'resource':
                        fillColor = 'lightblue';
                        break;
                    case 'action':
                        fillColor = 'lightcoral';
                        break;
                    case 'generator':
                        fillColor = 'lightgoldenrodyellow';
                        break;
                    case 'custom':
                    default:
                        fillColor = 'lightgray';
                        break;
                }
                node.attr('body/fill', fillColor);
                if (type !== 'custom' && type !== 'trigger') {
                    node.attr('pencilButton/display', 'none');
                    node.attr('pencilButtonOverlay/display', 'none');
                }
    
                node.position(clickPosition.x, clickPosition.y);
                const node_payload = {
                    node: node,
                    name: name,
                    node_type: type,
                    node_subtype: subtype,
                    is_new_node: true
                }
                if (subtype !== 'custom' && subtype !== 'trigger') {
                    node_payload.handler = subtype;
                }
                saveNode(node_payload);
            }
        });
        const $nodeTypeSelect = $('#add-node-type');
        const $nodeSubtypeSelect = $('#add-node-subtype');
        const $modal = $(`[data-name="add-node-dialog"]`);
        $nodeSubtypeSelect.select2({
            tags: true,
            dropdownParent: $modal
        });

        socket.emit(WorkflowEvent.NODE_GET_TYPES_REQUEST);
        waitForEvent(WorkflowEvent.NODE_GET_TYPES).then(data => {
            if (data.message === 'success') {
                $nodeTypeSelect.empty();
                data.node_types.forEach(type => {
                    $nodeTypeSelect.append(SelectOption(type));
                });

                const initialType = $nodeTypeSelect.val();
                fetchAndPopulateSubtypes(initialType);
            } else {
                toastr.error("Error fetching node types: " + data.error);
            }
        });

        $nodeTypeSelect.on('change', function() {
            const selectedType = $(this).val();
            fetchAndPopulateSubtypes(selectedType);
        });


        // function fetchAndPopulateSubtypes(nodeType) {
        //     socket.emit(WorkflowEvent.NODE_GET_SUBTYPES_REQUEST, { node_type: nodeType });
        //     // Corrected event wait: Should be NODE_GET_SUBTYPES, not NODE_GET_TYPES
        //     waitForEvent(WorkflowEvent.NODE_GET_SUBTYPES).then(subtypesData => {
        //         if (subtypesData.message === 'success') {
        //             // Preserve current value/tag before clearing
        //             const currentVal = $nodeSubtypeSelect.val();
        //             // Select2 with tags might return the tag text as value if it doesn't match an option
        //             const currentTagText = (currentVal && !$nodeSubtypeSelect.find(`option[value="${currentVal}"]`).length) ? currentVal : null;

        //             $nodeSubtypeSelect.empty(); // Clear existing options

        //             // Add fetched subtypes
        //             subtypesData.node_subtypes.forEach(subtype => {
        //                  // Ensure SelectOption generates <option value="subtype">subtype</option>
        //                  $nodeSubtypeSelect.append(SelectOption(subtype));
        //             });

        //             // Restore selection or tag
        //             if (currentVal && subtypesData.node_subtypes.includes(currentVal)) {
        //                 // If the previous value is in the new list, re-select it
        //                 $nodeSubtypeSelect.val(currentVal);
        //             } else if (currentTagText) {
        //                 // If it was a tag, create a new option for it and select it
        //                 // This ensures the user's typed input isn't lost when subtypes load
        //                 const newOption = new Option(currentTagText, currentTagText, true, true);
        //                 $nodeSubtypeSelect.append(newOption);
        //             }

        //             // Notify Select2 that options have changed
        //             $nodeSubtypeSelect.trigger('change.select2');

        //         } else {
        //             toastr.error("Error fetching node subtypes: " + subtypesData.error);
        //         }
        //     });
        // }

        function fetchAndPopulateSubtypes(nodeType) {
            socket.emit(WorkflowEvent.NODE_GET_SUBTYPES_REQUEST, { node_type: nodeType });
            waitForEvent(WorkflowEvent.NODE_GET_SUBTYPES).then(subtypesData => {
                if (subtypesData.message === 'success') {
                    $nodeSubtypeSelect.empty();
                    subtypesData.node_subtypes.forEach(subtype => {
                         $nodeSubtypeSelect.append(SelectOption(subtype));
                    });
                } else {
                    toastr.error("Error fetching node subtypes: " + subtypesData.error);
                }
            });
        }
        contextMenu.hide();
    });

    // Editor

    let editor;
    let currentEditingNode;

    function initCodeEditor() {
        if (!editor) {
            editor = createCodeEditor(document.getElementById('code-editor'));
            editor.refresh();
            editor.setSize('1024px', '768px');
        }
    }

    
    function openCodeEditor(elementView) {
        currentEditingNode = elementView.model;
        initCodeEditor();
        fetchNodeData(currentEditingNode.get('customId'), (node, data) => {
            editor.setValue(data.code);
            $('#code-editor-dialog').modal('show');
        });

        $('#code-editor-dialog').on('shown.bs.modal', function() {
            editor.refresh();
        });

        $(`#code-editor-dialog`).draggable({
            handle: ".modal-header"
        });

        $('#code-save').on('click', function() {
            if (currentEditingNode) {
                const content = editor.getValue();
                saveNode({
                    node: currentEditingNode,
                    name: currentEditingNode.attr('label/text'),
                    code: content
                });
            }
            $('#code-editor-dialog').modal('hide');
        });
        
        $('#code-cancel').on('click', function() {
            $('#code-editor-dialog').modal('hide');
        });

        $('#code-editor-dialog .modal-header .close').off('click').on('click', function() {
            $('#code-editor-dialog').modal('hide');
        });
    }

    //Links

    let selectedElements = [];
    let selectedElement = null;
    let contextMenu = $('#board-context-menu');
    let clickPosition = { x: 0, y: 0 };

    function showContextMenu(evt, x, y) {
        clickPosition = { x, y };
    
        const paperElement = paper.el;
        const paperRect = paperElement.getBoundingClientRect();
        const offsetX = evt.clientX - paperRect.left;
        const offsetY = evt.clientY - paperRect.top;
    
        const menuOffset = 10;
    
        contextMenu.css({
            display: 'block',
            left: offsetX + menuOffset,
            top: offsetY + menuOffset
        });
    }

    $('.paper-container').on('contextmenu', function(evt) {
        evt.preventDefault();
        const target = paper.findView(evt.target);
    
        if (!target) {
            selectedElement = null;
            const paperCoords = paper.clientToLocalPoint({ x: evt.clientX, y: evt.clientY });
            showContextMenu(evt, paperCoords.x, paperCoords.y);
    
            $('#board-create-link, #board-delete-link, #board-delete-node, #board-rename-window, #board-delete-note, #board-delete-window').hide();
            $('#board-add-node, #board-add-window, #board-add-note, #board-clear-nodes').show();
        }
    });

    paper.on('cell:contextmenu', function(cellView, evt, x, y) {
        evt.preventDefault();
        selectedElement = cellView.model;
        showContextMenu(evt, x, y);
    
        if (selectedElement instanceof joint.dia.Link) {
            $('#board-create-link, #board-add-node, #board-add-window, #board-clear-nodes, #board-delete-node, #board-rename-window, #board-add-note, #board-delete-window, #board-delete-note').hide();
            $('#board-delete-link').show();
        } else if (selectedElement instanceof joint.shapes.custom.NodeWithButton) {
            $('#board-create-link, #board-delete-node').show();
            $('#board-delete-link, #board-add-node, #board-add-window, #board-clear-nodes, #board-rename-window, #board-add-note, #board-delete-window, #board-delete-note').hide();
        } else if (selectedElement instanceof joint.shapes.custom.Window) {
            $('#board-rename-window, #board-add-node, #board-add-note, #board-delete-window').show();
            $('#board-create-link, #board-delete-link, #board-delete-node, #board-add-window, #board-clear-nodes, #board-delete-note').hide();
        } else if (selectedElement instanceof joint.shapes.custom.Note) {
            $('#board-delete-note').show();
            $('#board-create-link, #board-delete-link, #board-delete-node, #board-rename-window, #board-add-node, #board-add-window, #board-clear-nodes, #board-delete-window, #board-add-note').hide();
        } else {
            $('#board-create-link, #board-delete-link, #board-delete-node, #board-rename-window, #board-delete-window, #board-delete-note').hide();
            $('#board-add-node, #board-add-window, #board-clear-nodes, #board-add-note').show();
        }
    });

    $(document).on('click', function() {
        contextMenu.hide();
    });

    $('#board-create-link').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.shapes.custom.NodeWithButton) {
            if (!selectedElements.includes(selectedElement)) {
                selectedElements.push(selectedElement);
                if (selectedElements.length === 2) {
                    const sourceNode = selectedElements[0];
                    const targetNode = selectedElements[1];
    
                    const workflowId = $('#workflow-selector').val();
                    if (workflowId) {
                        const linkData = {
                            workflow_id: workflowId,
                            source: sourceNode.get('customId'),
                            target: targetNode.get('customId')
                        };
    
                        socket.emit(WorkflowEvent.LINK_CREATE_REQUEST, linkData);
                        waitForEvent(WorkflowEvent.LINK_CREATE).then(response => {
                            if (response.message === 'success') {
                                const newLink = getLink(graph, sourceNode, targetNode);
                                if (newLink) {
                                    newLink.addTo(graph);
                                    toastr.success("Link created successfully");
                                }
                            } else {
                                toastr.error("Error creating link: " + response.error);
                            }
                        });
                    } else {
                        toastr.warning("Please select a workflow to create the link.");
                    }
                    selectedElements = [];
                }
            }
        }
        contextMenu.hide();
    });

    $('#board-delete-link').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.dia.Link) {
            const workflowId = $('#workflow-selector').val();
            if (workflowId) {
                const sourceElement = graph.getCell(selectedElement.get('source').id);
                const targetElement = graph.getCell(selectedElement.get('target').id);
    
                if (sourceElement && targetElement) {
                    const sourceId = sourceElement.get('customId');
                    const targetId = targetElement.get('customId');
    
                    const linkData = {
                        workflow_id: workflowId,
                        source: sourceId,
                        target: targetId
                    };
    
                    socket.emit(WorkflowEvent.LINK_DELETE_REQUEST, linkData);
                    waitForEvent(WorkflowEvent.LINK_DELETE).then(response => {
                        if (response.message === 'success') {
                            selectedElement.remove();
                            toastr.success("Link deleted successfully");
                        } else {
                            toastr.error("Error deleting link: " + response.error);
                        }
                    });
                } else {
                    toastr.error("Source or target node not found.");
                }
            } else {
                toastr.warning("Please select a workflow to delete the link.");
            }
        }
        contextMenu.hide();
    });

    // nodes

    $('#board-add-window').click(function() {
        showNameDialog(function(name) {
            const window = getWindow(paper, name);
            window.position(clickPosition.x, clickPosition.y);
            window.addTo(graph);
        });
        contextMenu.hide();
    });

    $('#board-clear-nodes').click(function() {
        graph.clear();
        contextMenu.hide();
    });

    $('#board-rename-window').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.shapes.custom.Window) {
            const oldName = selectedElement.attr('label/text');
            showNameDialog(function(newName) {
                selectedElement.attr('label/text', newName);
            }, oldName);
        }
        contextMenu.hide();
    });

    $('#board-add-note').click(function() {
        const note = getNote(paper);
        note.position(clickPosition.x, clickPosition.y);
        note.addTo(graph);
        contextMenu.hide();
    });

    $('#board-delete-window').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.shapes.custom.Window) {
            selectedElement.remove();
        }
        contextMenu.hide();
    });
    
    $('#board-delete-note').on('click', function() {
        if (selectedElement && selectedElement instanceof joint.shapes.custom.Note) {
            selectedElement.remove();
        }
        contextMenu.hide();
    });

    // note

    paper.on('element:pointerdblclick', function(elementView, evt) {
        const element = elementView.model;
        if (element instanceof joint.shapes.custom.Note) {
            const currentText = $(element.attr('foreignObject/html')).html().replace(/<br>/g, '\n');
    
            const { x, y, width, height } = element.getBBox();
            const { tx, ty } = paper.translate();
            const { sx, sy } = paper.scale();
    
            const textareaX = (x * sx) + tx;
            const textareaY = (y * sy) + ty;
    
            const textarea = $('<textarea>')
                .css({
                    position: 'absolute',
                    zIndex: 999,
                    left: textareaX + 'px',
                    top: textareaY + 'px',
                    width: (width * sx) + 'px',
                    height: (height * sy) + 'px',
                    'font-family': 'Arial, sans-serif',
                    'font-size': '14px',
                    'line-height': '1.2em',
                    'white-space': 'pre-wrap',
                    'word-wrap': 'break-word',
                    'overflow-wrap': 'break-word',
                    padding: '5px',
                    border: 'none',
                    resize: 'none',
                    overflow: 'auto',
                    'box-sizing': 'border-box',
                    'text-align': 'left',
                    'vertical-align': 'top'
                })
                .val(currentText)
                .appendTo('.paper-container')
                .focus()
                .select();
    
            function saveText() {
                const newText = textarea.val();
                updateNoteText(element, newText);
                textarea.remove();
            }
    
            function handleClickOutside(e) {
                if (!$(e.target).is(textarea)) {
                    saveText();
                    $(document).off('mousedown', handleClickOutside);
                }
            }
    
            $(document).on('mousedown', handleClickOutside);
    
            textarea.on('mousedown', function(e) {
                e.stopPropagation();
            });
    
            textarea.on('keydown', function(e) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    saveText();
                    $(document).off('mousedown', handleClickOutside);
                }
            });
        }
    });
    
    // canvas zoom and panning

    let isPanning = false;
    let startPoint = { x: 0, y: 0 };
    let paperOrigin = { x: 0, y: 0 };

    $('.paper-container').on('mousedown', function(e) {
        const target = paper.findView(e.target);
        if (!target) {
            isPanning = true;
            startPoint = { x: e.pageX, y: e.pageY };
            paperOrigin = paper.translate();
            e.preventDefault();
        }
    });

    $(document).on('mousemove', function(e) {
        if (isPanning) {
            const dx = e.pageX - startPoint.x;
            const dy = e.pageY - startPoint.y;
            paper.translate(paperOrigin.tx + dx, paperOrigin.ty + dy);
        }
    });

    $(document).on('mouseup', function() {
        isPanning = false;
    });

    $('.paper-container').on('wheel', function(e) {
        e.preventDefault();
        const delta = e.originalEvent.deltaY;
        const oldScale = paper.scale().sx;
        const newScale = delta > 0 ? oldScale * 0.9 : oldScale * 1.1;
    
        const offsetX = e.offsetX;
        const offsetY = e.offsetY;
    
        const translate = paper.translate();
    
        const fx = (offsetX - translate.tx) / oldScale;
        const fy = (offsetY - translate.ty) / oldScale;
    
        const newTx = offsetX - fx * newScale;
        const newTy = offsetY - fy * newScale;
    
        paper.scale(newScale);
        paper.translate(newTx, newTy);
    });

    //elements drag and resize

    let isResizing = false;
    let isDragging = false;
    let resizeStartSize;
    let resizeStartPosition;
    let dragStartPosition;
    let resizeStartElementPosition;
    let nodesInsideWindow = [];
    let initialNodePositions = [];

    paper.on('element:pointerdown', function(elementView, evt, x, y) {
        const element = elementView.model;
        
        if (element instanceof joint.shapes.custom.Window || element instanceof joint.shapes.custom.Note) {
            const { width, height } = element.size();
            const { x: elementX, y: elementY } = element.position();
            
            if (x >= elementX + width - 10 && y >= elementY + height - 10) {
                isResizing = true;
                resizeStartSize = { width, height };
                resizeStartPosition = { x: evt.clientX, y: evt.clientY };
                resizeStartElementPosition = { x: elementX, y: elementY };
                evt.stopPropagation();
            } else {
                isDragging = true;
                dragStartPosition = { x: x - elementX, y: y - elementY };
                element.startBatch('move');
                
                if (element instanceof joint.shapes.custom.Window) {
                    nodesInsideWindow = graph.getElements().filter(node => node !== element && isNodeInsideWindow(node, element));
                    initialNodePositions = nodesInsideWindow.map(node => {
                        const nodePosition = node.position();
                        return {
                            node: node,
                            offsetX: nodePosition.x - elementX,
                            offsetY: nodePosition.y - elementY
                        };
                    });
                }
            }
        } else if (element.isElement()) {
            isDragging = true;
            dragStartPosition = { x: x - element.position().x, y: y - element.position().y };
            element.startBatch('move');
        }
    });

    paper.on('element:pointermove', function(elementView, evt, x, y) {
        const element = elementView.model;
        
        if (isResizing && (element instanceof joint.shapes.custom.Window || element instanceof joint.shapes.custom.Note)) {
            const dx = evt.clientX - resizeStartPosition.x;
            const dy = evt.clientY - resizeStartPosition.y;
            
            const newWidth = Math.max(50, resizeStartSize.width + dx);
            const newHeight = Math.max(50, resizeStartSize.height + dy);
            
            element.resize(newWidth, newHeight, { direction: 'bottom-right' });
            element.position(resizeStartElementPosition.x, resizeStartElementPosition.y);
        } else if (isDragging) {
            const newX = x - dragStartPosition.x;
            const newY = y - dragStartPosition.y;
            
            if (element instanceof joint.shapes.custom.Window) {
                const dx = newX - element.position().x;
                const dy = newY - element.position().y;
                
                element.position(newX, newY);
                
                initialNodePositions.forEach(({ node, offsetX, offsetY }) => {
                    node.position(newX + offsetX, newY + offsetY);
                });
            } else {
                element.position(newX, newY);
            }
        }
    });

    paper.on('element:pointerup', function(elementView) {
        const element = elementView.model;
        
        if (isDragging) {
            element.stopBatch('move');
        }
        
        isResizing = false;
        isDragging = false;
        dragStartPosition = null;
        resizeStartPosition = null;
        resizeStartSize = null;
        resizeStartElementPosition = null;
        nodesInsideWindow = [];
        initialNodePositions = [];
    });
}