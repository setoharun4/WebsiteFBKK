document.addEventListener("DOMContentLoaded", () => {
  const panelTabs = document.querySelectorAll(".panel-tab")
  const panelSections = document.querySelectorAll(".panel-section")

  function showPanel(panelId) {
    panelTabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.panel === panelId)
    })
    panelSections.forEach((panel) => {
      const isActive = panel.dataset.panel === panelId
      panel.classList.toggle("active", isActive)
      panel.hidden = !isActive
    })
    history.replaceState(null, "", `#${panelId}`)
  }

  panelTabs.forEach((tab) => {
    tab.addEventListener("click", () => showPanel(tab.dataset.panel))
  })

  const hash = window.location.hash.replace("#", "")
  const validPanels = ["sekolah", "akun"]
  const legacyPanels = {
    "tambah-sekolah": "sekolah",
    "daftar-sekolah": "sekolah",
    menunggu: "akun",
    terverifikasi: "akun",
  }
  const pendingCount = document.querySelector(".panel-tab-badge--warning")?.textContent?.trim()
  const resolvedPanel = legacyPanels[hash] || hash

  if (validPanels.includes(resolvedPanel)) {
    showPanel(resolvedPanel)
  } else if (pendingCount && pendingCount !== "0") {
    showPanel("akun")
  }

  const searchInput = document.getElementById("search-input")
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const keyword = searchInput.value.toLowerCase()
      document.querySelectorAll("#user-verification-table tbody tr[data-search]").forEach((row) => {
        row.style.display = row.dataset.search.includes(keyword) ? "" : "none"
      })
    })
  }

  document.querySelectorAll(".btn-verifikasi").forEach((button) => {
    button.addEventListener("click", () => {
      const userId = button.dataset.userId
      const row = button.closest("tr")
      const select = row.querySelector(".dropdown-sekolah")
      const idAnggota = select.value

      if (!idAnggota) {
        alert("Pilih sekolah terlebih dahulu")
        return
      }

      button.disabled = true
      fetch("/konfirmasi_verifikasi", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `user_id=${encodeURIComponent(userId)}&id_anggota=${encodeURIComponent(idAnggota)}`,
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            alert("Verifikasi berhasil")
            location.reload()
          } else {
            alert("Verifikasi gagal: " + (data.message || "Unknown error"))
            button.disabled = false
          }
        })
        .catch(() => {
          alert("Terjadi kesalahan")
          button.disabled = false
        })
    })
  })

  document.querySelectorAll(".btn-hapus-akun").forEach((button) => {
    button.addEventListener("click", () => {
      const userId = button.dataset.userId
      const row = button.closest("tr")
      const username = row.querySelector("td[data-label='Username']")?.textContent?.trim() || "akun ini"

      if (!confirm(`Hapus akun ${username} yang belum diverifikasi? Tindakan ini tidak dapat dibatalkan.`)) {
        return
      }

      button.disabled = true
      fetch(`/hapus_akun_tidak_verifikasi/${userId}`, { method: "POST" })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            row.remove()
          } else {
            alert("Gagal menghapus: " + (data.message || "Unknown error"))
            button.disabled = false
          }
        })
        .catch(() => {
          alert("Terjadi kesalahan")
          button.disabled = false
        })
    })
  })

  document.querySelectorAll(".btn-putus-akun").forEach((button) => {
    button.addEventListener("click", () => {
      const userId = button.dataset.userId
      const username = button.dataset.username
      const sekolah = button.dataset.sekolah

      const message =
        `Putus hubungan akun "${username}" dari "${sekolah}"?\n\n` +
        "Data tahunan dan laporan sekolah tetap tersimpan. Akun akan kembali ke status belum terverifikasi."

      if (!confirm(message)) {
        return
      }

      button.disabled = true
      fetch("/putus_akun_sekolah", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `user_id=${encodeURIComponent(userId)}`,
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            alert("Hubungan akun berhasil diputus")
            location.reload()
          } else {
            alert("Gagal memutus hubungan: " + (data.message || "Unknown error"))
            button.disabled = false
          }
        })
        .catch(() => {
          alert("Terjadi kesalahan")
          button.disabled = false
        })
    })
  })
})
