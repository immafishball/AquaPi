NiceSelect.bind(document.getElementById("timeRangeSelect"));

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM Content Loaded!");

  const temperatureCtx = document.getElementById("temperatureChart").getContext("2d");
  const pHctx = document.getElementById("pHChart").getContext("2d");

  const createDataset = (label, bgColor, borderColor) => ({
    label,
    data: [],
    backgroundColor: `${bgColor}0.1)`,
    borderColor: `${borderColor}1)`,
    borderWidth: 2,
    fill: true,
  });

  const temperatureChart = new Chart(temperatureCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        createDataset("Temperature (°C)", "rgba(255, 172, 100, ", "rgba(255, 172, 100, "),
        createDataset("Temperature (°F)", "rgba(195, 40, 96, ", "rgba(195, 40, 96, "),
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

  const pHChart = new Chart(pHctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        createDataset("pH Level", "rgba(75, 192, 192, ", "rgba(75, 192, 192, "),
      ],
    },
    options: {
      maintainAspectRatio: false,
      layout: { padding: 10 },
      responsive: true,
      legend: { position: "bottom" },
      title: { display: true, text: "pH Level Readings" },
      scales: {
        x: { type: "linear", position: "bottom" },
        y: { beginAtZero: true },
      },
    },
  });

  const fetchData = (temperatureUrl, pHUrl, callback) => () =>
    Promise.all([
      fetch(temperatureUrl).then(response => response.json()),
      fetch(pHUrl).then(response => response.json())
    ])
    .then(([temperatureData, pHData]) => callback(temperatureData, pHData))
    .catch(error => console.error(`Error fetching data:`, error));

  let maxDisplayedDataPoints = 10; // Initial value
  let temperatureEndpoint = "/get_temperature?timeRange=latest";
  let pHEndpoint = "/ph_level?timeRange=latest";
  let intervalId;

  const updateTemperatureChartData = (data) => {
    let celsius, fahrenheit, timestamp;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      temperatureChart.data.labels = [];
      temperatureChart.data.datasets[0].data = [];
      temperatureChart.data.datasets[1].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, celsius, fahrenheit] = datapoint;

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
      const lastDataPoint = newDataPoints[newDataPoints.length - 1];
      [timestamp, celsius, fahrenheit] = lastDataPoint;
    }

    if (temperatureChart.data.labels.length > maxDisplayedDataPoints) {
      temperatureChart.data.labels.shift();
      temperatureChart.data.datasets[0].data.shift();
      temperatureChart.data.datasets[1].data.shift();
    }

    temperatureChart.update();

    const currentTemperatureElement = document.getElementById("card-temperature");
    const currentTemperatureStatusElement = document.getElementById("card-temperature-status");
    currentTemperatureElement.innerHTML = `${celsius.toFixed(3)}°C / ${fahrenheit.toFixed(3)}°F`;

    let status;
    if (celsius >= 23 && celsius <= 27) {
      status = "Normal";
    } else if ((celsius >= 21 && celsius < 23) || (celsius > 27 && celsius <= 29)) {
      status = "Warning";
    } else {
      status = "Critical";
    }

    currentTemperatureStatusElement.innerHTML = status;
  };

  const updatepHChartData = (data) => {
    let pH, timestamp;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      pHChart.data.labels = [];
      pHChart.data.datasets[0].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, pH] = datapoint;

      let formattedDate;
      if (timeRangeSelect.value === "2") {
        formattedDate = new Date(timestamp).toLocaleString();
      } else {
        formattedDate = new Date(timestamp).toLocaleTimeString();
      }

      pHChart.data.labels.push(formattedDate);
      pHChart.data.datasets[0].data.push(pH.toFixed(2));
    });

    if (pHChart.data.labels.length > maxDisplayedDataPoints) {
      pHChart.data.labels.shift();
      pHChart.data.datasets[0].data.shift();
    }

    pHChart.update();

    const currentpHElement = document.getElementById("card-ph-level");
    const currentpHStatusElement = document.getElementById("card-ph-status");
    currentpHElement.innerHTML = `${pH.toFixed(2)}`;

    let status;
    if (pH >= 6.5 && pH <= 8.5) {
      status = "Normal";
    } else if (pH < 6.5 || pH > 8.5) {
      status = "Warning";
    } else {
      status = "Critical";
    }

    currentpHStatusElement.innerHTML = status;
  };

  const updateCharts = (temperatureData, pHData) => {
    updateTemperatureChartData(temperatureData);
    updatepHChartData(pHData);
  };

  const startInterval = (temperatureUrl, pHUrl) => {
    clearInterval(intervalId); // Clear previous interval
    const fetchDataCallback = fetchData(temperatureUrl, pHUrl, updateCharts);
    fetchDataCallback(); // Initial fetch
    intervalId = setInterval(fetchDataCallback, 5000);
  };

  startInterval(temperatureEndpoint, pHEndpoint);

  const timeRangeSelect = document.getElementById("timeRangeSelect");
  timeRangeSelect.addEventListener("change", () => {
    const selectedValue = timeRangeSelect.value;
    switch (selectedValue) {
      case "1":
        temperatureEndpoint = "/get_temperature?timeRange=lastHour";
        pHEndpoint = "/ph_level?timeRange=lastHour";
        break;
      case "2":
        temperatureEndpoint = "/get_temperature?timeRange=lastDay";
        pHEndpoint = "/ph_level?timeRange=lastDay";
        break;
      case "3":
        temperatureEndpoint = "/get_temperature?timeRange=lastMonth";
        pHEndpoint = "/ph_level?timeRange=lastMonth";
        break;
      default:
        temperatureEndpoint = "/get_temperature?timeRange=latest";
        pHEndpoint = "/ph_level?timeRange=latest";
    }
    startInterval(temperatureEndpoint, pHEndpoint);
  });

  function fetchWaterLevel() {
    fetch("/water_level")
      .then((response) => response.json())
      .then((data) => {
        const waterLevel = data.water_level;
        const currentWaterLevelElement = document.getElementById("card-water-level");
        currentWaterLevelElement.innerHTML = waterLevel;
      })
      .catch((error) => console.error("Error fetching water level:", error));
  }

  fetchWaterLevel(); 
  setInterval(fetchWaterLevel, 5000);

  function fetchTurbidity() {
    fetch("/turbidity")
      .then((response) => response.json())
      .then((data) => {
        const turbidity = data.turbidity[0];
        const currentTurbidityElement = document.getElementById("card-turbidity");
        currentTurbidityElement.innerHTML = turbidity;
        const currentTurbidityStatusElement = document.getElementById("card-turbidity-status");
        currentTurbidityStatusElement.innerHTML = data.turbidity[1];
      })
      .catch((error) => console.error("Error fetching turbidity:", error));
  }

  fetchTurbidity(); 
  setInterval(fetchTurbidity, 5000);
});
