const nextButton = document.querySelector(".btn-next");
const prevButton = document.querySelector(".btn-prev");
const steps = document.querySelectorAll(".step");
const form_steps = document.querySelectorAll(".form-step");
let active = 1;

nextButton.addEventListener("click", () => {
  active++;
  if (active > steps.length) {
    active = steps.length;
  }
  updateProgress();
});

prevButton.addEventListener("click", () => {
  active--;
  if (active < 0) {
    active = 1;
  }
  updateProgress();
});

const updateProgress = () => {
  console.log("steps.length =>" + steps.length);
  console.log("active => " + active);

  //toggle .active class for each list item
  steps.forEach((step, i) => {
    if (i == active - 1) {
      step.classList.add("active");
      form_steps[i].classList.add("active");
      console.log("i =>" + i);
    } else {
      step.classList.remove("active");
      form_steps[i].classList.remove("active");
    }
  });

  //enable or disable prev and next buttons
  if (active === 1) {
    prevButton.disabled = true;
  } else if (active === steps.length) {
    nextButton.disabled = true;
  } else {
    prevButton.disabled = false;
    nextButton.disabled = false;
  }
};

document.addEventListener("DOMContentLoaded", function () {
  // Get the value of the card-detected-fish element
  var detectedFish = document
    .getElementById("card-detected-fish")
    .innerText.trim();

  // Get the country dropdown element
  var fishTypeDropdown = document.getElementById("fish-type");

  // Loop through the options in the dropdown
  for (var i = 0; i < fishTypeDropdown.options.length; i++) {
    // Check if the text content of the option matches the detected fish
    if (fishTypeDropdown.options[i].text === detectedFish) {
      // Set the selected attribute to true
      fishTypeDropdown.options[i].selected = true;

      // Disable the dropdown
      fishTypeDropdown.disabled = true;

      break; // Exit the loop once a match is found
    }
  }

  let lastDetectedFish = { name: "--", confidence: 0 }; // Variable to store the last detected object
  let isDetectionPaused = false; // Flag to indicate whether object detection is paused

  function updateDetectedFish() {
    // If detection is paused (step 2), skip the detection logic
    if (active === 2) {
      return;
    }

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
