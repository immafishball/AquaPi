/* Clock */
const hours = document.querySelector(".hours");
const minutes = document.querySelector(".minutes");
const seconds = document.querySelector(".seconds");

clock = () => {
  let today = new Date();
  let h = (today.getHours() % 12) + today.getMinutes() / 59;
  let m = today.getMinutes();
  let s = today.getSeconds();

  h *= 30;
  m *= 6;
  s *= 6;

  rotation(hours, h);
  rotation(minutes, m);
  rotation(seconds, s);

  setTimeout(clock, 500);
};

rotation = (target, val) => {
  target.style.transform = `rotate(${val}deg)`;
};

window.onload = clock;

function toggleDiv() {
  $(".components").toggle();
  $(".components2").toggle();
}

function feednow() {
  fetch("/feed_now", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      $("#modalMessage").text(data.message);
      $("#messageModal").modal({ fadeDuration: 200 });
    })
    .catch((error) => {
      console.error("Error:", error);
      $("#modalMessage").text("Failed to control servo");
      $("#messageModal").modal({ fadeDuration: 200 });
    });
}

$(document).ready(function () {
  if (!$("#timepicker").data("mdtimepicker")) {
    $("#timepicker").mdtimepicker();
  }

  // Ensures only one event is bound
  $("#timepicker").off("timechanged").on("timechanged", function (e) {
    console.log("Selected time:", e.time);
    addStore(e);
  });

  addDiv(); // Load schedules on page load
});

function addStore(e) {
  if (!e.time) {
    console.error("No time value in event:", e);
    return;
  }

  const [hours, minutes] = e.time.split(":");

  $.ajax({
    type: "POST",
    url: "/add_schedule",
    contentType: "application/json;charset=UTF-8",
    data: JSON.stringify({ time: `${hours}:${minutes}` }),
    success: function (response) {
      console.log(response);
      addDiv(); // Refresh schedules after adding
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function showShort(id) {
  $("#time_" + id).toggle();
  $("#short_" + id).toggle();
}

function removeDiv(id) {
  $.ajax({
    type: "POST",
    url: "/remove_schedule",
    contentType: "application/json;charset=UTF-8",
    data: JSON.stringify({ id: id }),
    success: function (response) {
      console.log(response);
      addDiv(); // Refresh schedule list
    },
    error: function (error) {
      console.error(error);
    },
  });
}

function addDiv() {
  $.ajax({
    type: "GET",
    url: "/get_schedules",
    success: function (schedules) {
      $("#wrapper").empty();
      schedules.forEach(function (schedule) {
        let ts = schedule.time;
        var H = +ts.substr(0, 2);
        var h = H % 12 || 12;
        h = h < 10 ? "0" + h : h;
        var ampm = H < 12 ? " AM" : " PM";
        ts = h + ts.substr(2, 3) + ampm;

        const x = `
          <div id="${schedule.id}">
              <div class="btn2 btn__secondary2" onclick="showShort(${schedule.id})" id="main_${schedule.id}">
              <div id="time_${schedule.id}">${ts}</div>
              <div class="icon2" id="short_${schedule.id}" onclick="removeDiv(${schedule.id})">
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
