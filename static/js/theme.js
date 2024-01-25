const themeMap = {
  dark: "light",
  light: "solar",
  solar: "dark",
};

const theme =
  localStorage.getItem("theme") ||
  ((tmp = Object.keys(themeMap)[0]), localStorage.setItem("theme", tmp), tmp);
const bodyClass = document.body.classList;
bodyClass.add(theme);

function toggleTheme() {
  const current = localStorage.getItem("theme");
  const next = themeMap[current];

  bodyClass.replace(current, next);
  localStorage.setItem("theme", next);
}

let prevScrollPos = window.pageYOffset;
const navbar = document.querySelector(".navbar");

window.onscroll = function () {
  const currentScrollPos = window.pageYOffset;

  if (prevScrollPos > currentScrollPos) {
    // Scrolling up, show the navbar
    navbar.classList.remove("hidden");
  } else {
    // Scrolling down, hide the navbar
    navbar.classList.add("hidden");
  }

  prevScrollPos = currentScrollPos;
};

document.getElementById("themeButton").onclick = toggleTheme;
