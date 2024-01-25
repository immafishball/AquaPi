/*  clock */
const hours = document.querySelector(".hours");
const minutes = document.querySelector(".minutes");
const seconds = document.querySelector(".seconds");

clock = () => {
  let today = new Date();
  let h = (today.getHours() % 12) + today.getMinutes() / 59; // 22 % 12 = 10pm
  let m = today.getMinutes(); // 0 - 59
  let s = today.getSeconds(); // 0 - 59

  h *= 30; // 12 * 30 = 360deg
  m *= 6;
  s *= 6; // 60 * 6 = 360deg

  rotation(hours, h);
  rotation(minutes, m);
  rotation(seconds, s);

  // call every second
  setTimeout(clock, 500);
};

rotation = (target, val) => {
  target.style.transform = `rotate(${val}deg)`;
};

window.onload = clock();

function toggleDiv() {
  $(".components").toggle();
  $(".components2").toggle();
}

function feednow() {
  // You can customize this based on your needs
  fetch("/feed_now", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    // You can pass data if required
    body: JSON.stringify({
      // Add any data you want to send in the request body
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      // Handle the response from the server
      console.log(data);
      alert(data.message); // You can customize this based on your needs
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Failed to control servo"); // You can customize this based on your needs
    });
}

$(document).ready(function () {
  $("#timepicker").mdtimepicker(); //Initializes the time picker
  addDiv();
});

$("#timepicker")
  .mdtimepicker()
  .on("timechanged", function (e) {
    console.log(e.time);
    addStore(e);
  });

function addStore(e) {
  // Extract hours and minutes from the time string
  const [hours, minutes] = e.time.split(":");

  // Send the schedule time to Flask endpoint to store in SQLite
  $.ajax({
    type: "POST",
    url: "/add_schedule",
    contentType: "application/json;charset=UTF-8",
    data: JSON.stringify({ time: `${hours}:${minutes}` }), // Send only hours and minutes
    success: function (response) {
      console.log(response);
      addDiv();
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function showShort(id) {
  var idv = $(id)[0]["id"];
  $("#time_" + idv).toggle();
  $("#short_" + idv).toggle();
}

function removeDiv(id) {
  var idv = id;
  // Send the schedule id to Flask endpoint to remove from SQLite
  $.ajax({
    type: "POST",
    url: "/remove_schedule",
    contentType: "application/json;charset=UTF-8",
    data: JSON.stringify({ id: idv }),
    success: function (response) {
      console.log(response);
      addDiv();
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function addDiv() {
  // Request the schedule from Flask endpoint
  $.ajax({
    type: "GET",
    url: "/get_schedules",
    success: function (schedules) {
      $("#wrapper").html("");
      schedules.forEach(function (schedule) {
        let ts = schedule.time;
        var H = +ts.substr(0, 2);
        var h = H % 12 || 12;
        h = h < 10 ? "0" + h : h;
        var ampm = H < 12 ? " AM" : " PM";
        ts = h + ts.substr(2, 3) + ampm;

        const x = `
          <div id=${schedule.id}>
              <div class="btn2 btn__secondary2" onclick=showShort(${schedule.id}) id="main_${schedule.id}">
              <div id="time_${schedule.id}">
              ${ts}
              </div>
              <div class="icon2" id="short_${schedule.id}" onclick=removeDiv(${schedule.id})>
                  <div class="icon__add">
                      <ion-icon name="trash"></ion-icon>
                  </div>
              </div>
              </div>
          </div>`;
        $("#wrapper").append(x);
      });
    },
    error: function (error) {
      console.error(error);
    },
  });
}
