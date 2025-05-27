const rootStyles = getComputedStyle(document.documentElement);
const mainTextColor = rootStyles.getPropertyValue('--main-text-color').trim();
const messageColor = rootStyles.getPropertyValue('--user-messages-color').trim();
const borderColor = rootStyles.getPropertyValue('--ui-border-color').trim();
const primaryBgColor = rootStyles.getPropertyValue('--primary-bg-color').trim();

const DEFAULT_NODE_WIDTH = 150;
const DEFAULT_NODE_HEIGHT = 70;

export function initCustomShapes() {

    joint.shapes.custom = {};

    joint.shapes.custom.NodeWithButton = joint.shapes.standard.Rectangle.extend({
        markup: [{
            tagName: 'rect',
            selector: 'body'
        }, {
            tagName: 'rect',
            selector: 'header'
        }, {
            tagName: 'text',
            selector: 'label'
        }, {
            tagName: 'path',
            selector: 'eyeButton'
        }, {
            tagName: 'rect',
            selector: 'eyeButtonOverlay'
        }, {
            tagName: 'path',
            selector: 'pencilButton'
        }, {
            tagName: 'rect',
            selector: 'pencilButtonOverlay'
        }, {
            tagName: 'circle',
            selector: 'ledButton'
        }, {
            tagName: 'rect',
            selector: 'ledButtonOverlay'
        }, {
            tagName: 'line',
            selector: 'separator'
        }, {
            tagName: 'foreignObject',
            selector: 'interfaceForm'
        }],
        defaults: joint.util.deepSupplement({
            type: 'custom.NodeWithButton',
            interfaceVisible: false,
            originalSize: { width: DEFAULT_NODE_WIDTH, height: DEFAULT_NODE_HEIGHT },
            expandedSize: { width: 300, height: 250 },
            attrs: {
                body: {
                    fill: primaryBgColor,
                    stroke: borderColor,
                    strokeWidth: 0.5
                },
                header: {
                    fill: primaryBgColor,
                    stroke: 'none',
                    ref: 'body',
                    refWidth: '100%',
                    height: 20
                },
                label: { // Node name
                    text: 'Node',
                    fill: mainTextColor,
                    fontSize: 12,
                    fontFamily: 'Arial, helvetica, sans-serif',
                    ref: 'header',
                    refX: '50%',
                    refY: '50%',
                    xAlignment: 'middle',
                    yAlignment: 'middle'
                },
                eyeButton: {
                    d: 'M572.52 241.4C518.29 135.59 410.93 64 288 64S57.68 135.64 3.48 241.41a32.35 32.35 0 0 0 0 29.19C57.71 376.41 165.07 448 288 448s230.32-71.64 284.52-177.41a32.35 32.35 0 0 0 0-29.19zM288 400a144 144 0 1 1 144-144 143.93 143.93 0 0 1-144 144zm0-240a95.31 95.31 0 0 0-25.31 3.79 47.85 47.85 0 0 1-66.9 66.9A95.78 95.78 0 1 0 288 160z',
                    fill: mainTextColor,
                    ref: 'header',
                    refX: '90%',
                    refY: '50%',
                    width: 512,
                    height: 512,
                    transform: 'scale(0.025) translate(-256, -256)',
                    cursor: 'pointer'
                },
                eyeButtonOverlay: {
                    ref: 'header',
                    refX: '90%',
                    refY: '50%',
                    width: 16,
                    height: 16,
                    x: -8,
                    y: -8,
                    fill: 'transparent',
                    cursor: 'pointer',
                    event: 'element:eyeButton:pointerdown'
                },
                pencilButton: {
                    d: 'M497.9 142.1l-46.1 46.1c-4.7 4.7-12.3 4.7-17 0l-111-111c-4.7-4.7-4.7-12.3 0-17l46.1-46.1c18.7-18.7 49.1-18.7 67.9 0l60.1 60.1c18.8 18.7 18.8 49.1 0 67.9zM284.2 99.8L21.6 362.4.4 483.9c-2.9 16.4 11.4 30.6 27.8 27.8l121.5-21.3 262.6-262.6c4.7-4.7 4.7-12.3 0-17l-111-111c-4.8-4.7-12.4-4.7-17.1 0zM124.1 339.9c-5.5-5.5-5.5-14.3 0-19.8l154-154c5.5-5.5 14.3-5.5 19.8 0s5.5 14.3 0 19.8l-154 154c-5.5 5.5-14.3 5.5-19.8 0zM88 424h48v36.3l-64.5 11.3-31.1-31.1L51.7 376H88v48z',
                    fill: mainTextColor,
                    ref: 'header',
                    refX: '75%',
                    refY: '50%',
                    width: 512,
                    height: 512,
                    transform: 'scale(0.025) translate(-256, -256)',
                    cursor: 'pointer'
                },
                pencilButtonOverlay: {
                    ref: 'header',
                    refX: '75%',
                    refY: '50%',
                    width: 16,
                    height: 16,
                    x: -8,
                    y: -8,
                    fill: 'transparent',
                    cursor: 'pointer',
                    event: 'element:pencilButton:pointerdown'
                },
                ledButton: {
                    ref: 'header',
                    refX: '10%',
                    refY: '50%',
                    r: 6,
                    fill: 'green',
                    stroke: borderColor,
                    strokeWidth: 0.5,
                    cursor: 'pointer'
                },
                ledButtonOverlay: {
                    ref: 'header',
                    refX: '10%',
                    refY: '50%',
                    width: 16,
                    height: 16,
                    x: -8,
                    y: -8,
                    fill: 'transparent',
                    cursor: 'pointer',
                    event: 'element:ledButton:pointerdown'
                },
                separator: {
                    stroke: borderColor,
                    strokeWidth: 0.5,
                    ref: 'body',
                    refX: 0,
                    refY: 20,
                    refX2: '100%',
                    refY2: 20
                },
                interfaceForm: {
                    ref: 'body',
                    refX: 0,
                    refY: 20,
                    refWidth: '100%',
                    refHeight: 'calc(100% - 20px)',
                    overflow: 'auto',
                    display: 'none',
                    'background-color': 'rgba(255, 0, 0, 0.3)',
                }
            }
        }, joint.shapes.standard.Rectangle.prototype.defaults)
    });


    joint.shapes.custom.Window = joint.shapes.standard.Rectangle.extend({
        markup: [{
            tagName: 'rect',
            selector: 'body'
        }, {
            tagName: 'text',
            selector: 'label'
        }, {
            tagName: 'rect',
            selector: 'resizeHandle'
        }],
        defaults: joint.util.deepSupplement({
            type: 'custom.Window',
            attrs: {
                body: {
                    fill: 'lightgray',
                    stroke: 'black',
                    strokeWidth: 2
                },
                label: {
                    text: 'Window',
                    fill: 'black',
                    fontSize: 14,
                    refX: '50%',
                    refY: '10%',
                    xAlignment: 'middle',
                    yAlignment: 'middle'
                },
                resizeHandle: {
                    width: 10,
                    height: 10,
                    x: -10,
                    y: -10,
                    fill: 'black',
                    refX: '100%',
                    refY: '100%',
                    cursor: 'se-resize'
                }
            }
        }, joint.shapes.standard.Rectangle.prototype.defaults)
    });


    joint.shapes.custom.Note = joint.shapes.standard.Rectangle.extend({
        markup: [{
            tagName: 'rect',
            selector: 'body'
        }, {
            tagName: 'foreignObject',
            selector: 'foreignObject'
        }, {
            tagName: 'rect',
            selector: 'resizeHandle'
        }],
        defaults: joint.util.deepSupplement({
            type: 'custom.Note',
            attrs: {
                body: {
                    fill: messageColor,
                    stroke: borderColor,
                    strokeWidth: 1
                },
                foreignObject: {
                    refWidth: '100%',
                    refHeight: '100%',
                    refX: 0,
                    refY: 0,
                    overflow: 'hidden'
                },
                resizeHandle: {
                    width: 10,
                    height: 10,
                    x: -10,
                    y: -10,
                    fill: mainTextColor,
                    refX: '100%',
                    refY: '100%',
                    cursor: 'se-resize'
                }
            }
        }, joint.shapes.standard.Rectangle.prototype.defaults)
    });
}

export function updateNoteText(element, text) {
    const formattedText = text.replace(/\n/g, '<br>');
    const content = `<div xmlns="http://www.w3.org/1999/xhtml" style="width: 100%; height: 100%; padding: 5px; box-sizing: border-box; font-family: Arial, sans-serif; font-size: 14px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; line-height: 1.2em; text-align: left; vertical-align: top;">${formattedText}</div>`;
    element.attr('foreignObject/html', content);
}


export function getNode(paper, name) {
    const node = new joint.shapes.custom.NodeWithButton();
    
    const paperElement = paper.el;
    const paperRect = paperElement.getBoundingClientRect();
    const paperWidth = paperRect.width;
    const paperHeight = paperRect.height;
    
    const translate = paper.translate();
    const scale = paper.scale().sx;
    
    const centerX = (paperWidth / 2 - translate.tx) / scale;
    const centerY = (paperHeight / 2 - translate.ty) / scale;
    
    node.position(centerX - DEFAULT_NODE_WIDTH / 2, centerY - DEFAULT_NODE_HEIGHT / 2);
    node.resize(DEFAULT_NODE_WIDTH, DEFAULT_NODE_HEIGHT);
    node.attr('label/text', name || 'Node');

    return node;
}

export function getLink(graph, source, target) {
    const existingLink = graph.getLinks().find(link => 
        (link.get('source').id === source.id && link.get('target').id === target.id) ||
        (link.get('source').id === target.id && link.get('target').id === source.id)
    );

    if (existingLink) {
        return null;
    }

    const link = new joint.shapes.standard.Link();
    link.source(source);
    link.target(target);
    link.connector('smooth');

    return link;
}

export function getWindow(paper, name) {
    const window = new joint.shapes.custom.Window();
    
    const paperElement = paper.el;
    const paperRect = paperElement.getBoundingClientRect();
    const paperWidth = paperRect.width;
    const paperHeight = paperRect.height;
    
    const translate = paper.translate();
    const scale = paper.scale().sx;
    
    const centerX = (paperWidth / 2 - translate.tx) / scale;
    const centerY = (paperHeight / 2 - translate.ty) / scale;
    
    window.position(centerX - 100, centerY - 75);
    window.resize(200, 150);
    window.attr('label/text', name || 'Window');

    window.set('z', -2);

    return window;
}

export function getNote(paper, text) {
    const note = new joint.shapes.custom.Note();
    
    const paperElement = paper.el;
    const paperRect = paperElement.getBoundingClientRect();
    const paperWidth = paperRect.width;
    const paperHeight = paperRect.height;
    
    const translate = paper.translate();
    const scale = paper.scale().sx;
    
    const centerX = (paperWidth / 2 - translate.tx) / scale;
    const centerY = (paperHeight / 2 - translate.ty) / scale;
    
    note.position(centerX - 75, centerY - 50);
    note.resize(150, 100);
    updateNoteText(note, text || 'Double-click to edit');

    note.set('z', -1);

    return note;
}

export function setNodeZIndex(node) {
    node.set('z', 1);
}

export function adjustZIndex(graph) {
    graph.getElements().forEach(function(element) {
        if (element instanceof joint.shapes.custom.Window) {
            element.set('z', -2);
        } else if (element instanceof joint.shapes.custom.Note) {
            element.set('z', -1);
        } else {
            setNodeZIndex(element);
        }
    });
};

export function isNodeInsideWindow(node, window) {
    const nodeBox = node.getBBox();
    const windowBox = window.getBBox();
    return (
        nodeBox.x >= windowBox.x &&
        nodeBox.y >= windowBox.y &&
        nodeBox.x + nodeBox.width <= windowBox.x + windowBox.width &&
        nodeBox.y + nodeBox.height <= windowBox.y + windowBox.height
    );
}

export function setInterfaceHTML(element, html) {
    console.log('[shapes.js] setInterfaceHTML called. Element ID:', element.id, 'HTML to set (first 100 chars):', String(html).substring(0,100));
    const foreignObjectContent = `<div xmlns="http://www.w3.org/1999/xhtml" style="position: relative; width: 100%; height: 100%; overflow-y: auto; background-color: ${primaryBgColor}; color: ${mainTextColor}; padding: 5px; box-sizing: border-box; text-align: left;">${html}</div>`;
    element.attr('interfaceForm/html', foreignObjectContent);
}

export function toggleNodeInterface(node, paper) {
    const nodeId = node.get('customId') || node.id;
    console.log(`[shapes.js] toggleNodeInterface called for node: ${nodeId}. Current interfaceVisible: ${node.get('interfaceVisible')}`);
    const isVisible = node.get('interfaceVisible');
    const originalSize = node.get('originalSize');
    const expandedSize = node.get('expandedSize'); 

    if (isVisible) {
        node.resize(originalSize.width, originalSize.height);
        node.attr('interfaceForm/display', 'none');
        node.set('interfaceVisible', false);
        console.log(`[shapes.js] Node ${nodeId} interface hidden. New size:`, originalSize, "display: none");
    } else {
        const currentExpandedSize = node.get('expandedSize') || expandedSize;
        
        node.resize(currentExpandedSize.width, currentExpandedSize.height);
        
        const headerHeight = 20;
        node.attr('interfaceForm/width', currentExpandedSize.width);
        node.attr('interfaceForm/height', currentExpandedSize.height - headerHeight);
        node.attr('interfaceForm/display', 'block');
        node.set('interfaceVisible', true);
        node.toFront();
        console.log(`[shapes.js] Node ${nodeId} interface shown. Using size:`, currentExpandedSize, `FO dims: ${currentExpandedSize.width}x${currentExpandedSize.height - headerHeight}`, "display: block");
    }
    
    if (paper) {
        const elementView = paper.findViewByModel(node);
        if (elementView) {
            elementView.render(); 
            console.log(`[shapes.js] Called elementView.render() for node ${nodeId}`);
        } else {
            console.warn(`[shapes.js] ElementView not found for node ${nodeId} during paper update.`);
        }
    }
    console.log(`[shapes.js] toggleNodeInterface finished for node: ${nodeId}. New interfaceVisible: ${node.get('interfaceVisible')}`);
}