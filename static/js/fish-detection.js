document.addEventListener("DOMContentLoaded", function () {
  let lastDetectedFish = { name: "--", confidence: 0 }; // Variable to store the last detected object

  function updateDetectedFish() {
    // Fetch detected objects from the server
    fetch("/detect_objects")
      .then((response) => response.json())
      .then((data) => {
        // Extract the first detected object (you can modify this based on your logic)
        const newDetectedFish =
          data.length > 0
            ? {
                name: capitalizeFirstLetter(data[0].name),
                confidence: data[0].confidence,
              }
            : null;

        // Update the content of the card-detected-fish element only if it's a new object
        if (
          newDetectedFish !== null &&
          !areEqual(newDetectedFish, lastDetectedFish)
        ) {
          document.getElementById("card-detected-fish").textContent =
            newDetectedFish.name;
          document.getElementById(
            "card-confidence-level"
          ).textContent = `${newDetectedFish.confidence}%`;
          lastDetectedFish = { ...newDetectedFish }; // Copy the newDetectedFish object
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

  // Function to check if two objects are equal
  function areEqual(obj1, obj2) {
    return obj1.name === obj2.name && obj1.confidence === obj2.confidence;
  }

  // Call the updateDetectedFish function every 2 seconds (you can adjust the interval)
  setInterval(updateDetectedFish, 1000);
});
