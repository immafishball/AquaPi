NiceSelect.bind(document.getElementById("timeRangeSelect"));

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM Content Loaded!");
  const ctx = document.getElementById("temperatureChart").getContext("2d");
  const createDataset = (label, bgColor, borderColor) => ({
    label,
    data: [],
    backgroundColor: `${bgColor}0.1)`,
    borderColor: `${borderColor}1)`,
    borderWidth: 2,
    fill: true,
  });

  const temperatureChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        createDataset(
          "Temperature (°C)",
          "rgba(255, 172, 100, ",
          "rgba(255, 172, 100, "
        ),
        createDataset(
          "Temperature (°F)",
          "rgba(195, 40, 96, ",
          "rgba(195, 40, 96, "
        ),
      ],
    },
    options: {
      maintainAspectRatio: false,
      layout: { padding: 10 },
      responsive: true,
      legend: { position: "bottom" },
      title: { display: true, text: "Temperature Readings" },
      scales: {
        x: { type: "linear", position: "bottom" },
        y: { beginAtZero: true },
      },
    },
  });

  const fetchData = (url, callback) => () =>
    fetch(url)
      .then((response) => response.json())
      .then(callback)
      .catch((error) => console.error(`Error fetching ${url}:`, error));

  let maxDisplayedDataPoints = 10; // Initial value
  let currentEndpoint = "/get_temperature?timeRange=latest";
  let intervalId;

  const updateChartData = (data) => {
    let celsius, fahrenheit, timestamp; // Declare variables here
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      // Clear existing data for "lastHour" endpoint
      temperatureChart.data.labels = [];
      temperatureChart.data.datasets[0].data = [];
      temperatureChart.data.datasets[1].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, celsius, fahrenheit] = datapoint; // Assign values here

      // Format date differently based on the time range
      let formattedDate;
      if (timeRangeSelect.value === "2") {
        formattedDate = new Date(timestamp).toLocaleString();
      } else {
        formattedDate = new Date(timestamp).toLocaleTimeString();
      }

      temperatureChart.data.labels.push(formattedDate);
      temperatureChart.data.datasets[0].data.push(celsius.toFixed(3));
      temperatureChart.data.datasets[1].data.push(fahrenheit.toFixed(3));
    });

    if (newDataPoints.length > 0) {
      // Use the last data point values
      const lastDataPoint = newDataPoints[newDataPoints.length - 1];
      [timestamp, celsius, fahrenheit] = lastDataPoint;
    }

    if (temperatureChart.data.labels.length > maxDisplayedDataPoints) {
      temperatureChart.data.labels.shift();
      temperatureChart.data.datasets[0].data.shift();
      temperatureChart.data.datasets[1].data.shift();
    }

    temperatureChart.update();

    const currentTemperatureElement =
      document.getElementById("card-temperature");
    const lastEndpoint = isLastHourEndpoint
      ? "/get_temperature?timeRange=lastHour"
      : "/get_temperature?timeRange=latest";
    currentTemperatureElement.innerHTML = `${celsius.toFixed(
      3
    )}°C / ${fahrenheit.toFixed(3)}°F`;
  };

  const startInterval = (url) => {
    clearInterval(intervalId); // Clear previous interval
    const fetchDataCallback = fetchData(url, (data) => {
      if (url === "/get_temperature?timeRange=latest") {
        maxDisplayedDataPoints = 10; // Set max displayed data points to 10 for "Latest" endpoint
      } else {
        maxDisplayedDataPoints = data.length; // Set max displayed data points to the number of data points received
      }
      updateChartData(data);
    });
    fetchDataCallback(); // Initial fetch
    intervalId = setInterval(fetchDataCallback, 5000);
  };

  startInterval(currentEndpoint);
  const timeRangeSelect = document.getElementById("timeRangeSelect");
  timeRangeSelect.addEventListener("change", () => {
    // Call the relevant function or execute the necessary code
    // based on the selected value (hour/day/month).
    console.log("Selection changed:", timeRangeSelect.value);
  });
  // Add event listener for the select element
  document.getElementById("timeRangeSelect").addEventListener("change", () => {
    // Get the selected value
    const selectedValue = document.getElementById("timeRangeSelect").value;

    // Determine the endpoint based on the selected value
    switch (selectedValue) {
      case "1":
        currentEndpoint = "/get_temperature?timeRange=lastHour";
        break;
      case "2":
        currentEndpoint = "/get_temperature?timeRange=lastDay";
        break;
      case "3":
        currentEndpoint = "/get_temperature?timeRange=lastMonth";
        break;
      default:
        currentEndpoint = "/get_temperature?timeRange=latest";
      temperatureChart.data.labels.shift();
      temperatureChart.data.datasets[0].data.shift();
      temperatureChart.data.datasets[1].data.shift();
        temperatureChart.update();
    }

    // Start the interval with the determined endpoint
    startInterval(currentEndpoint);
  });

  function fetchWaterLevel() {
    fetch("/water_level") // Update the endpoint accordingly
      .then((response) => response.json())
      .then((data) => {
        const waterLevel = data.water_level;

        // Update water level value on the page
        const currentWaterLevelElement =
          document.getElementById("card-water-level");
        currentWaterLevelElement.innerHTML = waterLevel;
      })
      .catch((error) => console.error("Error fetching water level:", error));
  }

  fetchWaterLevel(); // Fetch water level data on page load

  // Set interval to fetch water level data periodically
  setInterval(fetchWaterLevel, 5000); // Adjust the interval as needed

  function fetchTurbidity() {
    fetch("/turbidity") // Update the endpoint accordingly
      .then((response) => response.json())
      .then((data) => {
        const turbidity = data.turbidity;

        // Update water level value on the page
        const currentTurbidityElement =
          document.getElementById("card-turbidity");
        currentTurbidityElement.innerHTML = turbidity;
      })
      .catch((error) => console.error("Error fetching turbidity:", error));
  }

  fetchTurbidity(); // Fetch water level data on page load

  // Set interval to fetch water level data periodically
  setInterval(fetchTurbidity, 5000); // Adjust the interval as needed
  
  function fetchpHLevel() {
    fetch("/ph_level") // Update the endpoint accordingly
      .then((response) => response.json())
      .then((data) => {
        const pH = data.pH;
// Convert the pH level to a string with two decimal places
let formattedPhLevel = pH.toFixed(2);

        // Update water level value on the page
        const currentpHElement =
          document.getElementById("card-ph-level");
        currentpHElement.innerHTML = formattedPhLevel;
      })
      .catch((error) => console.error("Error fetching ph level:", error));
  }

  fetchpHLevel(); // Fetch water level data on page load

  // Set interval to fetch water level data periodically
  setInterval(fetchpHLevel, 5000); // Adjust the interval as needed
});
