import { addPresetHandlers } from './scripts/preset/preset.js';
import { addApiHandlers } from './scripts/api.js';
import { addMessagesHandlers } from './scripts/messages.js';
import { addAgentsHandlers } from './scripts/agents.js';
import { addCardsHandlers } from './scripts/cards.js';
import { socket } from './scripts/socket.js';
import { showModal, toggleMenu, hideMenus } from './scripts/common.js'
import './scripts/interface.js';


socket.on('connect', function() {
    $(document).ready(function() {
        setInterval(() => {
            socket.emit('ping');
        }, 5000);
        $('select').select2();

        

        $(`#messager-button`).click(() => hideMenus());
        $('#preset-button').click(() => toggleMenu('#preset-menu-container'));
        $('#api-button').click(() => toggleMenu('#api-menu-container'));
        $('#settings-button').click(() => toggleMenu('#settings-menu-container'));
        $('#extra-button').click(() => toggleMenu('#extra-menu-container'));
        $('#persona-button').click(() => toggleMenu('#persona-menu-container'));
        $('#cards-button').click(() => toggleMenu('#cards-menu-container'));
        $('#agents-button').click(() => toggleMenu('#agents-menu-container'));
        $('#quick-button').click(() => showModal({ name: 'test', title: 'test', htmlContent: '<p>Это <strong>HTML</strong> контент</p>', buttonsOff: true, callback: () => {
            alert('Синхронный callback выполнен!');
        }}, true));

        addApiHandlers();
        addPresetHandlers();
        addAgentsHandlers();
        addCardsHandlers();
        addMessagesHandlers();

        $('#loading-screen').addClass('hidden');
        $('#main-container').removeClass('hidden');
    });
});
