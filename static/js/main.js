// FBKK — Main JS
document.addEventListener("DOMContentLoaded", () => {
  // Mobile navigation
  const toggle = document.querySelector(".nav-toggle")
  const menu = document.querySelector(".nav-menu")

  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      const open = menu.classList.toggle("open")
      toggle.setAttribute("aria-expanded", open)
      toggle.textContent = open ? "✕" : "☰"
    })

    document.addEventListener("click", (e) => {
      if (!toggle.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove("open")
        toggle.setAttribute("aria-expanded", "false")
        toggle.textContent = "☰"
      }
    })
  }

  // Active nav link
  const path = window.location.pathname
  document.querySelectorAll(".nav-link").forEach((link) => {
    if (link.getAttribute("href") === path) link.classList.add("active")
  })

  // Auto-hide flash messages
  document.querySelectorAll(".alert").forEach((alert) => {
    const close = alert.querySelector(".close-alert")
    setTimeout(() => alert.remove(), 5000)
    close?.addEventListener("click", () => alert.remove())
  })

  // Prevent double form submit
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const btn = form.querySelector('button[type="submit"]')
      if (btn && !btn.disabled) setTimeout(() => { btn.disabled = true }, 50)
    })
  })
})
