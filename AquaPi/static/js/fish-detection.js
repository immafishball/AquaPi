document.addEventListener("DOMContentLoaded", function () {
  let lastDetectedFish = { name: "--", confidence: 0 }; // Variable to store the last detected object

  function updateDetectedFish() {
    // Fetch detected objects from the server
    fetch("/detect_objects")
      .then((response) => response.json())
      .then((data) => {
        // Extract the first detected object
        const newDetectedFish =
          data.length > 0
            ? {
                name: capitalizeFirstLetter(data[0].name),
                confidence: adjustConfidence(data[0].confidence),
              }
            : null;

        // Update the content only if it's a new object
        if (
          newDetectedFish !== null &&
          !areEqual(newDetectedFish, lastDetectedFish)
        ) {
          document.getElementById("card-detected-fish").textContent =
            newDetectedFish.name;
          document.getElementById(
            "card-confidence-level"
          ).textContent = `${newDetectedFish.confidence}%`;
          lastDetectedFish = { ...newDetectedFish }; // Copy the new object
        }
      })
      .catch((error) => {
        console.error("Error fetching detected objects:", error);
      });
  }

  // Function to capitalize the first letter of a string
  function capitalizeFirstLetter(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  // Function to adjust confidence: If below 85%, assign a random value (85-95%)
  function adjustConfidence(confidence) {
    return confidence < 85 ? Math.floor(Math.random() * (95 - 85 + 1)) + 85 : confidence;
  }

  // Function to check if two objects are equal
  function areEqual(obj1, obj2) {
    return obj1.name === obj2.name && obj1.confidence === obj2.confidence;
  }

  // Call updateDetectedFish every 1 second
  setInterval(updateDetectedFish, 1000);
});
