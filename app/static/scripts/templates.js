export const ChatContainerId = '#chat-container'
export const AgentsContainerId = '#agents-menu-container'

export const MessageHolderClass = '.message-holder'
export const MessageClass = '.message'

export const EditorClass = '.message-editor-container'

//
//<div class="message-avatar-holder">
//    <img src="${card_avatar_uri}" alt="${card_name}" class="card-grid-item-avatar">
//</div>
//
export const Message = ({ id, parent_id, role, content, depth, card_id, card_version, card_name, card_avatar_uri, creation_time, modification_time }) => `
    <div class="message-holder" id="${id}" parent_id="${parent_id}" role="${role}" depth="${depth}" card_id="${card_id}" card_version="${card_version}">
        <div class="message-content-holder">
            <div class="message-buttons">
                <button class="edit-button">Edit</button>
                <button class="save-button">Save</button>
                <button class="cancel-button">Cancel</button>
                <button class="delete-button">Delete</button>
            </div>
            <div class="message">${content}</div>
        </div>
    </div>
`;


export const SelectOption = (value) => `
    <option value="${value}">${value}</option>
`;

export const NamedSelectOption = ({ value, name }) => `
    <option value="${value}">${name}</option>
`;

export const Editor = () => `
    <div class="message-editor-container"></div>
`;

export const ModalWindow = ({name, title, htmlContent}) => `
    <div class="modal fade" data-name="${name}" tabindex="-1" role="dialog" aria-labelledby="${name}Label" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
        <div class="modal-header">
            <h5 class="modal-title" id="${name}Label">${title}</h5>
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
            </button>
        </div>
        <div class="modal-body">
            ${htmlContent}
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
            <button type="button" class="btn btn-primary" data-name="${name}-callback">OK</button>
        </div>
        </div>
    </div>
    </div>
`;

export const ConfirmationModal = ({ name, title, message }) => `
    <div class="modal fade" id="${name}" tabindex="-1" role="dialog" aria-labelledby="${name}Label" aria-hidden="true">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="${name}Label">${title}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="${name}-confirm">Confirm</button>
                </div>
            </div>
        </div>
    </div>
`;

export const AddNodeDialog = () => `
    <form>
        <div class="form-group">
            <label for="add-node-name">Name:</label>
            <input type="text" id="add-node-name" class="form-control">
        </div>
        <div class="form-group">
            <label for="add-node-type">Type:</label>
            <select id="add-node-type" class="form-control">
            </select>
        </div>
        <div>
            <label for="add-node-subtype">Subtype:</label>
            <select id="add-node-subtype" class="form-control">
            </select>
        </div>
    </form>
`;


export const NewAgentDialog = () => `
    <form>
        <div class="form-group">
            <label for="new-agent-name">Name:</label>
            <input type="text" id="new-agent-name" class="form-control">
        </div>
        <br>
        <div class="form-group">
            <label for="new-agent-workflow">Workflow:</label>
            <select id="new-agent-workflow" class="form-control"></select>
        </div>
    </form>
`;

export const AgentItem = (id, name) => `
    <li class="ui-state-default item-layout agent-item" data-agent-id="${id}">
        <div class="item-name">${name}</div>
        <i class="fa-solid fa-toggle-off item-button agent-button-off"></i>
        <i class="fa-solid fa-toggle-on item-button agent-button-on"></i>
        <i class="fa-solid fa-arrow-rotate-right item-button agent-button-reinit"></i>
        <i class="fa-solid fa-pencil item-button agent-button-edit"></i>
        <i class="fa-solid fa-xmark item-button agent-button-delist"></i>
    </li>
`

export const NewAgentVarDialog = () => `
    <form>
        <div class="form-group">
            <label for="agent-var-name">Name:</label>
            <input type="text" id="agent-var-name" class="form-control">
        </div>
        <br>
        <div class="form-group">
            <label for="agent-var-type">Type:</label>
            <select id="agent-var-type" class="form-control">
                <option value="text">Text</option>
                <option value="array">Array</option>
                <option value="state-machine">State Machine</option>
            </select>
        </div>
    </form>
`;

export const AgentVarItem = (name) => `
    <li class="ui-state-default item-layout agent-var-item">
        <div class="item-name">${name}</div>
        <i class="fa-solid fa-eye item-button agent-var-button-view"></i>
        <i class="fa-solid fa-arrow-rotate-left item-button agent-var-button-reinit"></i>
        <i class="fa-solid fa-pencil item-button agent-var-button-edit"></i>
        <i class="fa-solid fa-trash item-button agent-var-button-delete"></i>
    </li>
`;

export const CardGridItem = ({id, version, name, avatar_uri}) => `
    <div class="card-grid-item" data-card-id="${id}" data-card-version="${version}">
        <img src="${avatar_uri}" alt="${name}" class="card-grid-item-avatar">
        <div class="card-grid-item-name">${name}</div>
        <div class="card-grid-item-buttons">
            <button class="btn btn-sm btn-light card-edit-button" title="Edit Card"><i class="fas fa-pencil-alt"></i></button>
        </div>
    </div>
`;

export const CardEditModalContent = (card) => `
    <form>
        <div class="form-group">
            <label for="card-edit-name">Card Name:</label>
            <input type="text" id="card-edit-name" class="form-control" value="${card.name || ''}">
        </div>
        <div class="form-group">
            <label for="card-edit-creator">Creator:</label>
            <input type="text" id="card-edit-creator" class="form-control" value="${card.creator || ''}">
        </div>
        <div class="form-group">
            <label for="card-edit-creator-note">Creator Note:</label>
            <textarea id="card-edit-creator-note" class="form-control" rows="3">${card.creator_note || ''}</textarea>
        </div>
        <div class="form-group">
            <label for="card-edit-tags">Tags (comma-separated):</label>
            <input type="text" id="card-edit-tags" class="form-control" value="${(card.tags || []).join(', ')}">
        </div>
    </form>
`;