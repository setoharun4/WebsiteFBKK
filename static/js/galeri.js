document.addEventListener("DOMContentLoaded", () => {
  const yearFilter = document.getElementById("filter-year")
  const galeriBase = window.location.pathname

  if (yearFilter) {
    yearFilter.addEventListener("change", () => {
      const year = yearFilter.value
      window.location.href = year === "all" ? galeriBase : `${galeriBase}?tahun=${year}`
    })
  }

  document.querySelectorAll(".galeri-card-clickable").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest("form, button")) return
      openPopup(card.dataset.id, card.dataset.judul)
    })
  })

  const overlay = document.getElementById("popup-overlay")
  const closeBtn = document.getElementById("popup-close")
  if (closeBtn) closeBtn.addEventListener("click", closePopup)
  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closePopup()
    })
  }

  const popupForm = document.getElementById("popup-upload-form")
  if (popupForm) {
    popupForm.addEventListener("submit", (e) => {
      e.preventDefault()
      const formData = new FormData(popupForm)
      formData.append("galeri_id", document.getElementById("popup-galeri-id").value)
      fetch("/galeri/upload_tambahan", { method: "POST", body: formData })
        .then((r) => r.json())
        .then((data) => {
          if (!data.success) {
            alert(data.error || "Upload gagal")
            return
          }
          appendPopupImage(data.foto_id, data.foto_path, true)
          popupForm.reset()
        })
        .catch(() => alert("Terjadi kesalahan saat upload"))
    })
  }
})

function openPopup(galeriId, judul) {
  fetch(`/galeri/${galeriId}/fotos`)
    .then((r) => r.json())
    .then((data) => {
      const container = document.getElementById("popup-images")
      const title = document.getElementById("popup-title")
      const galeriIdInput = document.getElementById("popup-galeri-id")
      container.innerHTML = ""
      title.textContent = judul || "Galeri"
      galeriIdInput.value = galeriId

      const isAdmin = data.length > 0 && typeof data[0] === "object" && data[0] !== null && "foto_path" in data[0]

      if (!data.length) {
        container.innerHTML = '<p class="empty-state">Belum ada foto dalam album ini.</p>'
      } else {
        data.forEach((foto) => {
          if (isAdmin) appendPopupImage(foto.id, foto.foto_path, true)
          else appendPopupImage(null, foto, false)
        })
      }

      document.getElementById("popup-overlay").classList.add("open")
    })
    .catch(() => alert("Gagal memuat foto galeri"))
}

function appendPopupImage(fotoId, fotoPath, canDelete) {
  const container = document.getElementById("popup-images")
  const wrapper = document.createElement("div")
  wrapper.className = "popup-img-wrapper"

  const img = document.createElement("img")
  img.src = `/static/${fotoPath}`
  img.alt = "Foto dokumentasi"
  img.className = "popup-img"
  wrapper.appendChild(img)

  if (canDelete && fotoId) {
    const deleteBtn = document.createElement("button")
    deleteBtn.type = "button"
    deleteBtn.textContent = "Hapus"
    deleteBtn.className = "btn btn-delete btn-sm"
    deleteBtn.addEventListener("click", () => {
      if (!confirm("Hapus foto ini?")) return
      fetch(`/foto/${fotoId}/hapus`, { method: "DELETE" })
        .then((r) => r.json())
        .then((result) => {
          if (result.success) wrapper.remove()
          else alert("Gagal menghapus foto")
        })
        .catch(() => alert("Terjadi kesalahan"))
    })
    wrapper.appendChild(deleteBtn)
  }

  container.appendChild(wrapper)
}

function closePopup() {
  document.getElementById("popup-overlay").classList.remove("open")
}
