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

  const fetchData = (temperatureUrl, pHUrl, waterLevelUrl, turbidityUrl, operationUrl, callback) => () =>
    Promise.all([
      fetch(temperatureUrl).then(response => response.json()),
      fetch(pHUrl).then(response => response.json()),
      fetch(waterLevelUrl).then(response => response.json()),
      fetch(turbidityUrl).then(response => response.json()),
      fetch(operationUrl).then(response => response.json())
    ])
    .then(([temperatureData, pHData, waterLevelData, turbidityData, operationData]) => callback(temperatureData, pHData, waterLevelData, turbidityData, operationData))
    .catch(error => console.error(`Error fetching data:`, error));

  let maxDisplayedDataPoints = 10; // Initial value
  let temperatureEndpoint = "/get_temperature?timeRange=latest";
  let pHEndpoint = "/get_ph_level?timeRange=latest";
  let waterLevelEndpoint = "/get_water_level?timeRange=latest";
  let turbidityEndpoint = "/get_turbidity?timeRange=latest";
  let operationEndpoint = "/get_operation?timeRange=latest";
  let intervalId;

  const updateTemperatureChartData = (data) => {
    let celsius, fahrenheit, timestamp, status;
    if (data.error && data.error === "Sensor not found") {
      temperatureChart.data.labels = [];
      temperatureChart.data.datasets[0].data = [];
      temperatureChart.data.datasets[1].data = [];
      temperatureChart.update();
      
      const currentTemperatureElement = document.getElementById("card-temperature");
      const currentTemperatureStatusElement = document.getElementById("card-temperature-status");
      currentTemperatureElement.innerHTML = "Not Found";
      currentTemperatureStatusElement.innerHTML = "No Data Available";
      return; // Exit early if no data available
    }

    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      temperatureChart.data.labels = [];
      temperatureChart.data.datasets[0].data = [];
      temperatureChart.data.datasets[1].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, celsius, fahrenheit, status] = datapoint;

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
      [timestamp, celsius, fahrenheit, status] = lastDataPoint;
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
    currentTemperatureStatusElement.innerHTML = status;
  };

  const updatepHChartData = (data) => {
    let pH, timestamp, status;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      pHChart.data.labels = [];
      pHChart.data.datasets[0].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, pH, status] = datapoint;

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
    currentpHStatusElement.innerHTML = status;
  };

  const updateWaterLevelData = (data) => {
    let water_level, timestamp;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      //waterLevel.data.labels = [];
      //waterLevel.data.datasets[0].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, water_level] = datapoint;

      let formattedDate;
      if (timeRangeSelect.value === "2") {
        formattedDate = new Date(timestamp).toLocaleString();
      } else {
        formattedDate = new Date(timestamp).toLocaleTimeString();
      }

      //waterLevel.data.labels.push(formattedDate);
      //waterLevel.data.datasets[0].data.push(pH.toFixed(2));
    });

    //if (waterLevel.data.labels.length > maxDisplayedDataPoints) {
      //waterLevel.data.labels.shift();
      //waterLevel.data.datasets[0].data.shift();
    //}

    //waterLevel.update();

    const currentwaterLevelElement = document.getElementById("card-water-level");
    //const currentwaterLevelStatusElement = document.getElementById("card-ph-status");
    currentwaterLevelElement.innerHTML = water_level;
    //currentwaterLevelStatusElement.innerHTML = status;
  };

  const updateTurbidityData = (data) => {
    let turbidity, timestamp, status;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      //turbidity.data.labels = [];
      //turbidity.data.datasets[0].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, turbidity, status] = datapoint;

      let formattedDate;
      if (timeRangeSelect.value === "2") {
        formattedDate = new Date(timestamp).toLocaleString();
      } else {
        formattedDate = new Date(timestamp).toLocaleTimeString();
      }

      //turbidity.data.labels.push(formattedDate);
      //turbidity.data.datasets[0].data.push(pH.toFixed(2));
    });

    //if (turbidity.data.labels.length > maxDisplayedDataPoints) {
      //turbidity.data.labels.shift();
      //turbidity.data.datasets[0].data.shift();
    //}

    //turbidity.update();

    const currentturbidityElement = document.getElementById("card-turbidity");
    const currentturbidityStatusElement = document.getElementById("card-turbidity-status");
    currentturbidityElement.innerHTML = `${turbidity.toFixed(2)}` + " NTU";
    currentturbidityStatusElement.innerHTML = status;
  };

  const updateOperationData = (data) => {
    let operation, timestamp, status;
    const isLastHourEndpoint = data[0] && Array.isArray(data[0]);
    const newDataPoints = isLastHourEndpoint ? data : [data];

    if (isLastHourEndpoint) {
      //turbidity.data.labels = [];
      //turbidity.data.datasets[0].data = [];
    }

    newDataPoints.forEach((datapoint) => {
      [timestamp, operation, status] = datapoint;

      let formattedDate;
      if (timeRangeSelect.value === "2") {
        formattedDate = new Date(timestamp).toLocaleString();
      } else {
        formattedDate = new Date(timestamp).toLocaleTimeString();
      }

      //turbidity.data.labels.push(formattedDate);
      //turbidity.data.datasets[0].data.push(pH.toFixed(2));
    });

    //if (turbidity.data.labels.length > maxDisplayedDataPoints) {
      //turbidity.data.labels.shift();
      //turbidity.data.datasets[0].data.shift();
    //}

    //turbidity.update();

    const currentoperationElement = document.getElementById("card-operation");
    const currentoperationStatusElement = document.getElementById("card-operation-status");
    currentoperationElement.innerHTML = operation;
    currentoperationStatusElement.innerHTML = status;
  };

  const updateCharts = (temperatureData, pHData, waterLevelData, turbidityData, operationData) => {
    updateTemperatureChartData(temperatureData);
    updatepHChartData(pHData);
    updateWaterLevelData(waterLevelData);
    updateTurbidityData(turbidityData);
    updateOperationData(operationData)
  };

  const startInterval = (temperatureUrl, pHUrl, waterLevelUrl, turbidityUrl, operationUrl) => {
    clearInterval(intervalId); // Clear previous interval
    const fetchDataCallback = fetchData(temperatureUrl, pHUrl, waterLevelUrl, turbidityUrl, operationUrl, updateCharts);
    fetchDataCallback(); // Initial fetch
    intervalId = setInterval(fetchDataCallback, 5000);
  };

  startInterval(temperatureEndpoint, pHEndpoint, waterLevelEndpoint, turbidityEndpoint, operationEndpoint);

  const timeRangeSelect = document.getElementById("timeRangeSelect");
  timeRangeSelect.addEventListener("change", () => {
    const selectedValue = timeRangeSelect.value;
    switch (selectedValue) {
      case "1":
        temperatureEndpoint = "/get_temperature?timeRange=lastHour";
        pHEndpoint = "/get_ph_level?timeRange=lastHour";
        waterLevelEndpoint = "/get_water_level?timeRange=lastHour";
        turbidityEndpoint = "/get_turbidity?timeRange=lastHour";
        operationEndpoint = "/get_operation?timeRange=lastHour";
        break;
      case "2":
        temperatureEndpoint = "/get_temperature?timeRange=lastDay";
        pHEndpoint = "/get_ph_level?timeRange=lastDay";
        waterLevelEndpoint = "/get_water_level?timeRange=lastDay";
        turbidityEndpoint = "/get_turbidity?timeRange=lastDay";
        operationEndpoint = "/get_operation?timeRange=lastDay";
        break;
      case "3":
        temperatureEndpoint = "/get_temperature?timeRange=lastMonth";
        pHEndpoint = "/get_ph_level?timeRange=lastMonth";
        waterLevelEndpoint = "/get_water_level?timeRange=lastMonth";
        turbidityEndpoint = "/get_turbidity?timeRange=lastMonth";
        operationEndpoint = "/get_operation?timeRange=lastMonth";
        break;
      default:
        temperatureEndpoint = "/get_temperature?timeRange=latest";
        pHEndpoint = "/get_ph_level?timeRange=latest";
        waterLevelEndpoint = "/get_water_level?timeRange=latest";
        turbidityEndpoint = "/get_turbidity?timeRange=latest";
        operationEndpoint = "/get_operation?timeRange=latest";
    }
    startInterval(temperatureEndpoint, pHEndpoint, waterLevelEndpoint, turbidityEndpoint, operationEndpoint)
  });
});
