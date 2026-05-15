// Function to find and modify textareas
function modifyTextareas() {
  const textareas = document.querySelectorAll('textarea');
  textareas.forEach(area => {
    // Set new content only if it's currently empty
    if (!area.value) {
      area.value = "Content modified by my extension!";
      area.addEventListener('click', function(){
		alert("working");
	});
      // Notify the page that the value has changed
      area.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
}

// Run the script when the page is fully loaded
window.addEventListener('load', modifyTextareas);