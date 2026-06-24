document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-baca-notifikasi").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id
      const item = btn.closest(".notifikasi-item")
      const link = item?.dataset.link

      btn.disabled = true
      fetch(`/notifikasi/${id}/baca`, { method: "POST" })
        .then((r) => r.json())
        .then((data) => {
          if (!data.success) {
            alert(data.message || "Gagal memperbarui notifikasi")
            btn.disabled = false
            return
          }
          if (data.link_url || link) {
            window.location.href = data.link_url || link
            return
          }
          item?.classList.remove("notifikasi-item--unread")
          btn.replaceWith(Object.assign(document.createElement("span"), {
            className: "notifikasi-status-read",
            textContent: "Sudah dibaca",
          }))
        })
        .catch(() => {
          alert("Terjadi kesalahan")
          btn.disabled = false
        })
    })
  })
})
