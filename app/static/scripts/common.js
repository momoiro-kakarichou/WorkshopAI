import { ModalWindow, ConfirmationModal } from './templates.js'

export const current_context = {
    card_id: null,
    chat_id: null,
    chat_len: null
}


export const MessageRole = {
    SYSTEM: 'system',
    USER: 'user',
    ASSISTANT: 'assistant'
};

export const menus = [
    '#preset-menu-container',
    '#api-menu-container',
    '#settings-menu-container',
    '#extra-menu-container',
    '#persona-menu-container',
    '#cards-menu-container',
    '#agents-menu-container'
];

export const toggleMenu = (menuClass) => {
    menus.forEach(menu => { if (menu !== menuClass) $(menu).addClass('hidden') });
    $(menuClass).toggleClass('hidden');
};

export const hideMenus = () => {
    menus.forEach(menu => { $(menu).addClass('hidden') });
}

export function showNameDialog(callback, oldName) {
    if (oldName) {
        $('#name').val(oldName);
    }

    $('#name-dialog').modal({ animation: false }).modal('show');

    $(`#name-dialog`).draggable({
        handle: ".modal-header"
    });

    $('#name-dialog-ok').off('click').on('click', function() {
        const name = $('#name').val();
        callback(name);
        $('#name-dialog').modal('hide');
    });

    $('#name-dialog-cancel').off('click').on('click', function() {
        $('#name-dialog').modal('hide');
    });

    $('#name-dialog .modal-header .close').off('click').on('click', function() {
        $('#name-dialog').modal('hide');
    });

    $('#name-dialog').on('shown.bs.modal', function() {
        $('#name').trigger('focus').select();
    });

    $('#name-dialog').on('hidden.bs.modal', function() {
        $('#name').val('');
    });
}

export function showModal({ name, title, htmlContent, callback, allowInteraction = false, customStyles = {}, buttonsOff = false, position = null }) {
    const existingModal = $(`[data-name="${name}"]`);
    if (existingModal.length) {
        existingModal.modal('hide');
        existingModal.on('hidden.bs.modal', function () {
            $(this).remove();
        });
    }

    const modalHTML = ModalWindow({ name: name, title: title, htmlContent: htmlContent })
  
    $('body').append(modalHTML);

    const modalOptions = allowInteraction ? { backdrop: false, keyboard: false, animation: false } : { animation: false };

    const $modal = $(`[data-name="${name}"]`);
    
    const $modalDialog = $modal.find('.modal-dialog');
    
    if (position) {
        $modal.css({
            'display': 'block',
            'overflow': 'visible'
        });
        $modalDialog.css({
            'position': 'fixed',
            'margin': '0',
            ...position
        });
        try { $modalDialog.draggable('destroy'); } catch (e) { /* ignore if not initialized */ }
    } else {
        $modal.css({
            'display': '',
            'overflow': ''
        });
        $modalDialog.css({
            'position': '',
            'margin': '',
            'top': '',
            'left': '',
            'right': '',
            'bottom': ''
        });
        $modalDialog.draggable({
            handle: ".modal-header"
        });
    }

    $modal.modal(modalOptions);
    $modal.modal('show');

    if (allowInteraction) {
        $modal.css('pointer-events', 'none');
        $modal.find('.modal-dialog').css('pointer-events', 'auto');
    }

    for (const [selector, styles] of Object.entries(customStyles)) {
        $modal.find(selector).css(styles);
    }

    if (buttonsOff) {
        $modal.find('.modal-footer').hide();
    }

    $modal.find(`[data-name="${name}-callback"]`).on('click', async function() {
        if (callback && typeof callback === 'function') {
            if (callback.constructor.name === 'AsyncFunction') {
                await callback();
            } else {
                callback();
            }
        }
        $modal.modal('hide');
    });

    $modal.find('.close, [data-dismiss="modal"]').on('click', function() {
        $modal.modal('hide');
    });

    $modal.on('hidden.bs.modal', function () {
        $(this).remove();
    });
  }

export function showConfirmationModal({ title, message, onConfirm }) {
    const modalId = 'confirmation-modal';
    const modalHtml = ConfirmationModal({
        name: modalId,
        title: title,
        message: message
    });

    $(`#${modalId}`).remove();

    $('body').append(modalHtml);

    $(`#${modalId}`).modal({ animation: false }).modal('show');

    $(`#${modalId}-confirm`).on('click', function () {
        $(`#${modalId}`).modal('hide');
        onConfirm();
    });

    $(`#${modalId}`).find('.close, [data-dismiss="modal"]').on('click', function() {
        $(`#${modalId}`).modal('hide');
    });

    $(`#${modalId}`).on('hidden.bs.modal', function () {
        $(this).remove();
    });
}