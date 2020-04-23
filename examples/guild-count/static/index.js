// You make POST requests as you would normally do in javascript.

function submitForm() {
    var formData = JSON.stringify($("#myForm").serializeArray());
    $.ajax({
        type: "POST",
        url: "/",
        data: formData,
        success: function(){console.log("Success")},
        dataType: "json",
        contentType: "application/json"
    })
}