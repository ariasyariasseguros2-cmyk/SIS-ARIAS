document.addEventListener("DOMContentLoaded", function() {
    // Check if the element exists to avoid errors
    var submitBtn = document.getElementById("submit-btn");
    if (submitBtn) {
        submitBtn.addEventListener("click", function(event) {
            // Prevent default form submission
            event.preventDefault();
            
            // Call the function to extract amounts if defined
            if (typeof extractAmounts === 'function') {
                extractAmounts();
            }
        });
    }
});
