$(document).ready(function() {

    $('[id^="desc-"]').not('[id$="-toggle"]').hide();

    // Attach a click event listener to the toggle div
    $('[id^="desc-"][id$="-toggle"]').click(function() {
        // Get the ID of the clicked toggle div
        var toggleId = $(this).attr('id');

        // Extract the part of the ID related to the note.id
        var noteId = toggleId.replace('-toggle', '');

        var descDiv = $('#' + noteId);
        descDiv.toggle();

        // Update the text of the toggle button depending on whether the description div is visible or not
        if (descDiv.is(':visible')) {
            $(this).text('Hide description');
        } else {
            $(this).text('Show description');
        }
    });
});