import { socket, waitForEvent } from './socket.js';
import { SelectOption, NamedSelectOption } from './templates.js';
import { showNameDialog } from './common.js';

const module_prefix = '[API]:'
const CHAT_COMPLETIONS_API = 'chat_completions';

export function addApiHandlers() {
    // api chat completions button clicked
    $('#api-chat-completions').click(() => {
        $('#api-chat-completion-config').toggleClass('hidden');
        socket.emit('api_source_request', { api_type: CHAT_COMPLETIONS_API });
        waitForEvent('api_source').then((msg) => {
            if (msg.success === false) {
                toastr.error(msg.error || 'Failed to load API sources.');
                return;
            }
            $('#cc_source').html(msg.api_sources.map(SelectOption).join('')).trigger('change');
        }).catch(err => {
            console.error(`${module_prefix} Error fetching API sources:`, err);
            toastr.error('Error fetching API sources.');
        });
    });

    // api source change
    $('#cc_source').change(function() {
        const selectedValue = $(this).val();
        socket.emit('api_list_request', { api_type: CHAT_COMPLETIONS_API, source: selectedValue });
        waitForEvent('api_list').then((msg) => {
            if (msg.success === false) {
                toastr.error(msg.error || 'Failed to load API presets.');
                $('#cc_preset').html('').trigger('change');
                return;
            }
            const data = msg.data || msg;
            if (Array.isArray(data)) {
                 $('#cc_preset').html(data.map(item => NamedSelectOption({ value: item.id, name: item.name })).join('')).trigger('change');
            } else {
                 console.warn(`${module_prefix} Unexpected data structure for api_list:`, msg);
                 toastr.warning('Received unexpected data for API presets.');
                 $('#cc_preset').html('').trigger('change');
            }
        }).catch(err => {
            console.error(`${module_prefix} Error fetching API list:`, err);
            toastr.error('Error fetching API presets.');
            $('#cc_preset').html('').trigger('change');
        });

        socket.emit('api_model_request', { api_type: CHAT_COMPLETIONS_API, source: selectedValue });
        waitForEvent('api_model').then((msg) => {
             if (msg.success === false) {
                toastr.error(msg.error || 'Failed to load API models.');
                return;
            }
            $('#cc_model').html(msg.api_models.map(SelectOption).join(''));
            $('#cc_model').select2({ tags: true });
        }).catch(err => {
            console.error(`${module_prefix} Error fetching API models:`, err);
            toastr.error('Error fetching API models.');
        });
    });


    $('#cc_preset').change(function() {
        const selectedValue = $(this).val();
        if (selectedValue) {
            const source = $('#cc_source').val();
            socket.emit('api_request', { api_type: CHAT_COMPLETIONS_API, source, id: selectedValue });
            waitForEvent('api').then((msg) => {
                if (msg.success === false) {
                    toastr.error(msg.error || 'Failed to load API details.');
                    return;
                }
                $('#cc_name').val(msg.name);
                $('#cc_url').val(msg.api_url);
                $('#cc_password').val(msg.api_key);
                const modelSelect = $('#cc_model');
                const modelValue = msg.model;
                if (modelValue && modelSelect.find(`option[value='${modelValue}']`).length === 0) {
                    const newOption = new Option(modelValue, modelValue, true, true);
                    modelSelect.append(newOption);
                }
                modelSelect.val(modelValue).trigger('change');
                $('#cc_tags').val(msg.tags ? msg.tags.join(', ') : 'default');
            }).catch(err => {
                console.error(`${module_prefix} Error fetching API details:`, err);
                toastr.error('Error fetching API details.');
            });
        } else {
            $('#cc_name').val('');
            $('#cc_url').val('');
            $('#cc_password').val('');
            $('#cc_model').val(null).trigger('change');
            $('#cc_tags').val('default');
        }
    });

    // api save
    $('#cc-save-preset-button').on('click', function(event) {
        event.preventDefault();
        const source = $('#cc_source').val();
        const name = $('#cc_name').val();
        const url = $('#cc_url').val();
        const password = $('#cc_password').val();
        const model = $('#cc_model').val();
        const id = $('#cc_preset').val();
        const tagsString = $('#cc_tags').val();
        const tags = tagsString ? tagsString.split(',').map(tag => tag.trim()).filter(tag => tag) : ['default'];
        if (tags.length === 0) {
            tags.push('default');
        }

        socket.emit('api_save_request', {
            source, name, api_url: url, api_key: password, model, api_type: CHAT_COMPLETIONS_API, id, tags
        });

        waitForEvent('api_save').then((msg) => {
            if (msg.success === false) {
                 toastr.error(msg.error || 'Failed to save API.');
                 return;
            }
            toastr.success(msg.message || 'API saved successfully.');
            socket.emit('api_list_request', { api_type: CHAT_COMPLETIONS_API, source });
            waitForEvent('api_list').then((listMsg) => {
                 if (listMsg.success === false) {
                    toastr.error(listMsg.error || 'Failed to refresh API presets.');
                    return;
                 }
                 const data = listMsg.data || listMsg;
                 if (Array.isArray(data)) {
                    $('#cc_preset').html(data.map(item => NamedSelectOption({ value: item.id, name: item.name })).join('')).val(msg.id);
                 } else {
                    console.warn(`${module_prefix} Unexpected data structure for api_list after save:`, listMsg);
                    toastr.warning('Received unexpected data for API presets after save.');
                 }
            }).catch(err => {
                console.error(`${module_prefix} Error fetching API list after save:`, err);
                toastr.error('Error refreshing API presets after save.');
            });
        }).catch(err => {
             console.error(`${module_prefix} Error saving API:`, err);
             toastr.error('Error saving API.');
        });
    });

    // api delete
    $('#cc-delete-preset-button').on('click', function(event) {
        event.preventDefault();
        const source = $('#cc_source').val();
        const id = $('#cc_preset').val();

        socket.emit('api_delete_request', { id, source, api_type: CHAT_COMPLETIONS_API });

        waitForEvent('api_delete').then((msg) => {
             if (msg.success === false) {
                 toastr.error(msg.error || 'Failed to delete API.');
                 return;
             }
            toastr.success(msg.message || 'API deleted successfully.');
            socket.emit('api_list_request', { api_type: CHAT_COMPLETIONS_API, source });
             waitForEvent('api_list').then((listMsg) => {
                 if (listMsg.success === false) {
                    toastr.error(listMsg.error || 'Failed to refresh API presets.');
                    return;
                 }
                 const data = listMsg.data || listMsg;
                 if (Array.isArray(data)) {
                    $('#cc_preset').html(data.map(item => NamedSelectOption({ value: item.id, name: item.name })).join('')).trigger('change');
                 } else {
                    console.warn(`${module_prefix} Unexpected data structure for api_list after delete:`, listMsg);
                    toastr.warning('Received unexpected data for API presets after delete.');
                 }
            }).catch(err => {
                console.error(`${module_prefix} Error fetching API list after delete:`, err);
                toastr.error('Error refreshing API presets after delete.');
            });
        }).catch(err => {
            console.error(`${module_prefix} Error deleting API:`, err);
            toastr.error('Error deleting API.');
        });
    });

    // api refresh models
    $('#cc-refresh-models-button').on('click', function(event) {
        event.preventDefault();
        const apiUrl = $('#cc_url').val();
        const apiKey = $('#cc_password').val();
        const source = $('#cc_source').val();

        if (!apiUrl) {
            toastr.error('Base URL must be set to fetch models.');
            return;
        }

        toastr.info('Fetching models...');

        socket.emit('api_fetch_external_models_request', {
            api_url: apiUrl,
            api_key: apiKey,
            api_type: CHAT_COMPLETIONS_API,
            source: source
        });

        waitForEvent('api_fetch_external_models_response').then((msg) => {
            if (msg.success === false) {
                toastr.error(msg.error || 'Failed to fetch external models.');
                return;
            }
            
            const modelSelect = $('#cc_model');
            const currentModelVal = modelSelect.val();
            const existingModels = new Set(modelSelect.find('option').map((_, opt) => $(opt).val()).get());

            if (msg.models && Array.isArray(msg.models)) {
                let newModelsAdded = 0;
                msg.models.forEach(model => {
                    let modelId, modelName;
                    if (typeof model === 'string') {
                        modelId = model;
                        modelName = model;
                    } else if (typeof model === 'object' && model !== null && model.id) {
                        modelId = model.id;
                        modelName = model.name || model.id;
                    } else {
                        console.warn(`${module_prefix} Skipping invalid model structure:`, model);
                        return;
                    }

                    if (!existingModels.has(modelId)) {
                        const newOption = new Option(modelName, modelId, false, false);
                        modelSelect.append(newOption);
                        existingModels.add(modelId);
                        newModelsAdded++;
                    }
                });
                modelSelect.val(currentModelVal).trigger('change.select2');
                toastr.success(`Fetched ${newModelsAdded} new model(s). Total models: ${existingModels.size}.`);
            } else {
                toastr.warning('No new models found or unexpected response format.');
            }
        }).catch(err => {
            console.error(`${module_prefix} Error fetching external models:`, err);
            toastr.error('Error fetching external models.');
        });
    });

    // api new preset
    $('#cc-new-preset-button').on('click', function(event) {
        event.preventDefault();
        showNameDialog((newName) => {
            if (newName) {
                $('#cc_preset').val('').trigger('change');
                $('#cc_name').val(newName);
                $('#cc_url').val('');
                $('#cc_password').val('');
                $('#cc_model').val(null).trigger('change');
                $('#cc_tags').val('default');
            }
        });
    });
}