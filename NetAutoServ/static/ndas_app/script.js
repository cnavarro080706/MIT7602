const hamBurger = document.querySelector(".toggle-btn");

hamBurger.addEventListener("click", function () {
  // Toggle the expand class on sidebar and footer
  document.querySelector("#sidebar").classList.toggle("expand");
  document.querySelector("footer").classList.toggle("expand");
});

// const hamBurger = document.querySelector(".toggle-btn");
// // const toggleIcon = document.querySelector(".toggle-icon");

// hamBurger.addEventListener("click", function () {
//   // Toggle the expand class on sidebar
//   document.querySelector("#sidebar").classList.toggle("expand");
//   document.querySelector("footer").classList.toggle("expand");

//   // Change the icon based on the sidebar state
//   if (sidebar.classList.contains("expand"))
//     {
//     toggleIcon.classList.remove("bi bi-arrow-right-circle-fill"); // Remove right arrow
//     toggleIcon.classList.add("bi bi-arrow-left-circle-fill"); // Add left arrow
//   } else {
//     toggleIcon.classList.remove("bi bi-arrow-left-circle-fill"); // Remove left arrow
//     toggleIcon.classList.add("bi bi-arrow-right-circle-fill"); // Add right arrow
//   }
// });