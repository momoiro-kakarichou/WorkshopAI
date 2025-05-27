toastr.options.progressBar = true;
toastr.options.preventDuplicates = true;

export function wrapTextInQuotes(text) {
    const regex = /<p>(.*?)<\/p>/g;

    const replaceQuotes = (match, p1) => {
        return '<p>' + p1.replace(/(?:&quot;|")([^&"]*?)(?:&quot;|")/g, '<q>$1</q>') + '</p>';
    };
    return text.replace(regex, replaceQuotes);
}

export function ensureNewline(text) {
    var regex = /(?<!\n)\n(?!\n)/g;
    text = text.replace(regex, '  \n');
    return text;
}

export function escapeMathJaxDelimiters(text) {
    return text
        .replace(/\\\(/g, '\\\\(')
        .replace(/\\\)/g, '\\\\)')
        .replace(/\\\[/g, '\\\\[')
        .replace(/\\\]/g, '\\\\]');
}

export function escapeDoubleBackslashes(text) {
    return text.replace(/\\/g, '\\\\');
}

export function wrapTextInCustomMarkdown(text) {
    text = escapeDoubleBackslashes(text);
    text = escapeMathJaxDelimiters(text);
    text = ensureNewline(text);
    text = marked.parse(text);
    text = wrapTextInQuotes(text);

    return text;
}

export function highlightMessagesCodes() {
    const codesToHighlight = $('.message code');

    codesToHighlight.each(function() {
        hljs.highlightElement(this);
    });
}

export function highlightMessageCodes(message) {
    const codesToHighlight = message.find('code');

    codesToHighlight.each(function() {
        hljs.highlightElement(this);
    });
}

export function createQuillEditor(container) {
    return new Quill(container, {
        theme: 'snow',
        modules: {
            toolbar: false
        }
    });
}

export function createCodeEditor(container) {
    const editor = CodeMirror(container, {
        mode: "python",
        theme: "default",
        lineNumbers: true,
        indentUnit: 4,
        tabSize: 4,
        indentWithTabs: true,
        autofocus: true,
        lineWrapping: true,
        extraKeys: {
            "Tab": function(cm) {
                if (cm.somethingSelected()) {
                    cm.indentSelection("add");
                } else {
                    cm.replaceSelection("    ", "end", "+input");
                }
            }
        }
    });

    editor.setOption("lineNumberFormatter", function(line) {
        return line + " ";
    });

    setTimeout(() => {
        editor.refresh();
        editor.getWrapperElement().style.paddingLeft = "10px";
    }, 0);

    return editor;
}

export function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}