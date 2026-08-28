function split(val) {
    return val.split(/,\s*/);
}

function extractLast(term) {
    return split(term).pop();
}

$(function() {
    var autocompleteUrl = document.getElementById("tag-autocomplete-script").dataset.autocompleteUrl;

    $("#id_tags") // Django's default ID for the 'tags' field
        .on("keydown", function(event) {
            // Check if the autocomplete menu is visible and an item is focused
            var isMenuOpen = $(this).autocomplete("instance").menu.element.is(":visible");
            var hasActiveItem = $(this).autocomplete("instance").menu.active;

            if (event.keyCode === $.ui.keyCode.TAB && isMenuOpen && hasActiveItem) {
                event.preventDefault();
            }
        })
        .autocomplete({
            source: function(request, response) {
                $.getJSON(autocompleteUrl, {
                    term: extractLast(request.term)
                }, response);
            },
            search: function() {
                // custom minLength: only search if the last term is at least 2 chars
                var term = extractLast(this.value);
                if (term.length < 2) { return false; }
            },
            focus: function() {
                // prevent value inserted on focus
                return false;
            },
            select: function(event, ui) {
                var terms = split(this.value);
                // remove the current input
                terms.pop();
                // add the selected item, plus a placeholder to get the comma-and-space at the end
                terms.push(ui.item.value, "");
                this.value = terms.join(", ");
                return false;
            }
        });
});
