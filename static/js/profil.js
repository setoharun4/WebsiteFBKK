function fetchData() {
  const search = document.getElementById("search").value
  const sortBy = document.getElementById("sort_by").value
  fetch(`/get_anggota?search=${encodeURIComponent(search)}&sort_by=${sortBy}`)
    .then((r) => r.json())
    .then((res) => {
      if (!res.success) return
      const tbody = document.getElementById("anggota-tbody")
      const isDisnaker = document.getElementById("modal") !== null
      tbody.innerHTML = res.data.map((row, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${isDisnaker ? `<a href="#" class="open-modal link" data-sekolah="${row.id}">${row.sekolah}</a>` : row.sekolah}</td>
          <td>${row.alamat}</td>
          <td>${row.kecamatan}</td>
        </tr>`).join("")
      attachModalListeners()
    })
}

document.addEventListener("DOMContentLoaded", () => {
  attachModalListeners()

  const toggleScroll = document.getElementById("toggle-scroll")
  const tableContainer = document.querySelector(".anggota-table-container")

  if (toggleScroll && tableContainer) {
    const savedState = localStorage.getItem("table_scrollable")
    if (savedState !== null) {
      const isScrollable = savedState === "true"
      toggleScroll.checked = isScrollable
      if (isScrollable) {
        tableContainer.classList.add("scrollable")
      } else {
        tableContainer.classList.remove("scrollable")
      }
    } else {
      tableContainer.classList.add("scrollable")
      toggleScroll.checked = true
    }

    toggleScroll.addEventListener("change", () => {
      if (toggleScroll.checked) {
        tableContainer.classList.add("scrollable")
        localStorage.setItem("table_scrollable", "true")
      } else {
        tableContainer.classList.remove("scrollable")
        localStorage.setItem("table_scrollable", "false")
      }
    })
  }
})

function attachModalListeners() {
  const modal = document.getElementById("modal")
  if (!modal) return

  const modalTitle = document.getElementById("modal-title")
  const modalBody = document.getElementById("modal-body")
  const closeModal = modal.querySelector(".close-modal")

  document.querySelectorAll(".open-modal").forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault()
      const idSekolah = item.getAttribute("data-sekolah")
      modalBody.innerHTML = '<tr><td colspan="6" class="no-data">Memuat data...</td></tr>'
      modalTitle.textContent = "Memuat..."

      fetch(`/get_data_tahunan/${idSekolah}`)
        .then((r) => r.json())
        .then((data) => {
          modalBody.innerHTML = ""
          if (data.success) {
            modalTitle.textContent = `Data Tahunan: ${data.sekolah || "Sekolah"}`
            if (!data.data.length) {
              modalBody.innerHTML = '<tr><td colspan="6" class="no-data">Belum ada data</td></tr>'
            } else {
              data.data.forEach((row) => {
                modalBody.innerHTML += `<tr>
                  <td>${row.tahun}</td><td>${row.kerja}</td><td>${row.kuliah}</td>
                  <td>${row.wirausaha}</td><td>${row.belum_bekerja}</td><td>${row.total}</td></tr>`
              })
            }
          } else {
            modalTitle.textContent = "Terjadi Kesalahan"
            modalBody.innerHTML = `<tr><td colspan="6">${data.error || "Gagal"}</td></tr>`
          }
        })
        .catch(() => {
          modalTitle.textContent = "Terjadi Kesalahan"
          modalBody.innerHTML = '<tr><td colspan="6">Gagal mengambil data</td></tr>'
        })

      modal.classList.add("open")
    })
  })

  if (closeModal) closeModal.addEventListener("click", () => modal.classList.remove("open"))
  modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.classList.remove("open")
  })
}
