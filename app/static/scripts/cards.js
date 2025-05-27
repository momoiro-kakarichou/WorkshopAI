import { socket, waitForEvent, CardEvent, ChatEvent } from './socket.js';
import { showNameDialog, hideMenus, current_context, showModal } from './common.js'
import { CardGridItem, CardEditModalContent } from './templates.js'

const module_prefix = '[CARDS]:'
const CardsGridContainerId = '#cards-grid-container'

export function addCardsHandlers() {
    function fetchCardsList(callback) {
        socket.emit(CardEvent.CARD_LIST_REQUEST);
        waitForEvent(CardEvent.CARD_LIST).then(data => {
            callback(data.cards);
        });
    }

    function refreshCardsList(searchTerm = '') {
        fetchCardsList((cards) => {
            const card_grid_container = $(CardsGridContainerId);
            const lowerSearchTerm = searchTerm.toLowerCase();
            const filteredCards = cards.filter(card =>
                card.name.toLowerCase().includes(lowerSearchTerm)
            );
            card_grid_container.html(filteredCards.map(CardGridItem).join(''));
        })
    }

    $('#cards-button').click(() => {
        if ($('#cards-menu-container').is(':visible')) {
            refreshCardsList();
        }
    });

    $('#cards-panel-search').on('input', function() {
        const searchTerm = $(this).val();
        refreshCardsList(searchTerm);
    });

    $(CardsGridContainerId).on('click', '.card-grid-item', function() {
        const cardItem = $(this);
        const cardId = cardItem.data('card-id');
        const cardVersion = cardItem.data('card-version');

        if (cardId && cardVersion) {
            console.log(`${module_prefix} Requesting chat for card_id: ${cardId}, card_version: ${cardVersion}`);
            socket.emit(ChatEvent.GET_OR_CREATE_LATEST_CHAT_REQUEST, {
                card_id: cardId,
                card_version: cardVersion
            });
            waitForEvent(ChatEvent.GET_OR_CREATE_LATEST_CHAT).then(response => {
                if (response.status === 'success') {
                    const chat_id = response.chat_id;
                    current_context.chat_id = chat_id;
                    socket.emit(ChatEvent.CHAT_REQUEST, {
                        chat_id: chat_id
                    });
                    hideMenus();
                } else {
                    toastr.error("Error loading chat: " + response.message);
                }
            });
        } else {
            console.error(`${module_prefix} Could not find card_id or card_version for the clicked item.`);
        }
    });

    $(CardsGridContainerId).on('click', '.card-edit-button', function(event) {
        event.stopPropagation();
        const cardItem = $(this).closest('.card-grid-item');
        const cardId = cardItem.data('card-id');
        const cardVersion = cardItem.data('card-version');

        if (cardId && cardVersion) {
            socket.emit(CardEvent.CARD_REQUEST, { id: cardId, version: cardVersion });
            waitForEvent(CardEvent.CARD).then(response => {
                if (response.card) {
                    const cardData = response.card;
                    showModal({
                        name: 'card-edit-modal',
                        title: `Edit Card: ${cardData.name}`,
                        htmlContent: CardEditModalContent(cardData),
                        callback: () => {
                            const newName = $('#card-edit-name').val();
                            const newCreator = $('#card-edit-creator').val();
                            const newCreatorNote = $('#card-edit-creator-note').val();
                            const newTags = $('#card-edit-tags').val().split(',').map(tag => tag.trim()).filter(tag => tag);

                            if (!newName) {
                                toastr.warning("Card name cannot be empty.");
                                return;
                            }

                            const updatePayload = {
                                id: cardId,
                                version: cardVersion,
                                name: newName,
                                creator: newCreator,
                                creator_note: newCreatorNote,
                                tags: newTags,
                            };

                            socket.emit(CardEvent.CARD_SAVE_REQUEST, updatePayload);
                            waitForEvent(CardEvent.CARD_SAVE).then(saveResponse => {
                                if (saveResponse.message === 'success') {
                                    refreshCardsList();
                                    toastr.success("Card updated successfully.");
                                } else {
                                    toastr.error("Error updating card: " + saveResponse.error);
                                }
                            });
                        }
                    });
                } else {
                    toastr.error("Error fetching card details: " + (response.error || "Unknown error"));
                }
            });
        } else {
            console.error(`${module_prefix} Could not find card_id or card_version for editing.`);
            toastr.error("Error preparing card for editing.");
        }
    });

    $('#cards-panel-button-new').click(() => {
        showNameDialog((cardName) => {
            if (cardName) {
                const cardData = {
                    name: cardName,
                };
                socket.emit(CardEvent.CARD_SAVE_REQUEST, cardData);
                waitForEvent(CardEvent.CARD_SAVE).then(response => {
                    if (response.message === 'success') {
                        refreshCardsList();
                        toastr.success("Card added");
                    } else {
                        toastr.error("Error adding card: " + response.error);
                    }
                });
            }
        });
    });
}