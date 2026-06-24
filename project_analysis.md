# Analisis Proyek Website FBKK Jember

Website FBKK (Forum Bursa Kerja Khusus) Jember adalah platform web berbasis Python Flask yang dirancang untuk memfasilitasi Dinas Tenaga Kerja (Disnaker) Kabupaten Jember dalam memantau dan mengelola data kelulusan serta keterserapan tenaga kerja dari berbagai Sekolah Menengah Kejuruan (SMK) di Kabupaten Jember.

Berikut adalah penjelasan detail mengenai struktur proyek, skema database, fungsionalitas pengguna, serta teknologi yang digunakan.

## 🛠️ Tech Stack (Teknologi yang Digunakan)
1. **Backend (Python Flask)**:
   - `Flask (v2.3.3)` sebagai framework utama.
   - `PyMySQL (v1.1.0)` sebagai driver koneksi ke database MySQL/MariaDB.
   - `Werkzeug (v2.3.7)` untuk utilitas keamanan seperti hashing password (`generate_password_hash` & `check_password_hash`) dan penanganan file upload (`secure_filename`).
2. **Frontend**:
   - **Template Engine**: Jinja2 (bawaan Flask) untuk rendering halaman HTML dinamis dari server.
   - **Styling**: CSS Kustom (`static/css/style.css`) dengan desain clean dan modern.
   - **Interaktivitas**: Vanilla JavaScript (`static/js/`) yang dibagi menjadi beberapa modul fungsional:
     - `main.js`: Logika umum seperti navigasi mobile, link aktif, alert otomatis, dan proteksi double submit.
     - `profil.js`: Pencarian dan pengurutan dinamis daftar profil sekolah anggota.
     - `galeri.js`: Penanganan penayangan foto kegiatan dan pengelolaan galeri (khusus admin).
     - `notifikasi.js`: Penanganan interaksi notifikasi (membaca, menandai telah dibaca).
     - `verifikasi.js`: Logika konfirmasi verifikasi pendaftaran akun sekolah anggota baru.
3. **Database**:
   - MySQL/MariaDB dengan skema relational terstruktur.
4. **Next.js Boilerplate**:
   - Terdapat folder `app`, `components`, `hooks`, `lib`, `package.json`, dan `tsconfig.json` yang berisi boilerplate Next.js (kemungkinan dari implementasi v0 sebelumnya atau persiapan migrasi ke Next.js). Saat ini backend utama yang aktif adalah Flask di port 5000.

---

## 📂 Struktur Direktori Proyek
```text
WebsiteFBKK/
├── app/                  # Boilerplate aplikasi Next.js (tidak aktif)
├── components/           # Komponen UI Next.js (tidak aktif)
├── hooks/                # Custom React Hooks (tidak aktif)
├── lib/                  # Utilitas Next.js (tidak aktif)
├── database/             # File SQL skema dan data awal
│   ├── schema.sql        # Skema awal database fbkk_db
│   ├── seed.sql          # Data awal (seeding) untuk testing
│   └── migrate_features.sql # SQL untuk migrasi fitur galeri & notif
├── static/               # Aset statis Flask
│   ├── css/              # Berisi style.css
│   ├── js/               # JavaScript modul (main, profil, galeri, dll.)
│   ├── img/              # Gambar & logo statis
│   └── uploads/          # Folder upload laporan & dokumen kegiatan
├── templates/            # Template HTML Jinja2 untuk halaman web
│   ├── partials/         # Komponen HTML modular (sidebar, dll.)
│   ├── base.html         # Template dasar (layout utama)
│   ├── home.html         # Halaman utama (landing page)
│   ├── login.html        # Halaman login
│   ├── dashboard_...     # Dashboard anggota & disnaker
│   └── ...
├── server_improved.py    # Main program/server Flask
├── config.py             # File konfigurasi server
├── setup_database.py     # Script inisialisasi awal database
├── migrate_database.py   # Script Python migrasi skema database
├── requirements.txt      # Dependensi Python
└── package.json          # Dependensi Node.js (untuk Next.js)
```

---

## 🗄️ Skema Database (`fbkk_db`)
Database terdiri dari 7 tabel utama dengan hubungan relasional yang saling terikat:
1. **`users`**: Menyimpan data akun pengguna.
   - `role`: `'fbkk'` (sekolah) atau `'disnaker'` (admin Disnaker).
   - `is_verified`: Status verifikasi akun sekolah (0 = belum, 1 = sudah).
2. **`anggota_fbkk`**: Menyimpan profil detail sekolah SMK anggota.
   - Relasi ke `users.user_id` untuk menghubungkan akun login dengan profil sekolah.
   - Kolom status: `'Negeri'` atau `'Swasta'`.
3. **`data_tahunan`**: Menyimpan data kelulusan tahunan untuk tiap sekolah.
   - Menyimpan metrik: `jumlah_lulusan`, `lanjut_bekerja`, `kuliah`, `wirausaha`, `belum_bekerja`, `jumlah_mitra` (perusahaan mitra), dan status kepemilikan sertifikat tanda daftar BKK (`tanda_daftar_bkk`).
4. **`laporan`**: Menyimpan riwayat dokumen laporan berkala yang diunggah oleh sekolah anggota.
5. **`informasi`**: Menyimpan artikel/pengumuman penting yang dipublikasikan oleh Disnaker.
6. **`galeri` & `foto_galeri`**: Menyimpan galeri foto kegiatan. Skema ini mendukung relasi *One-to-Many* di mana satu galeri kegiatan dapat menampung banyak foto kegiatan.
7. **`notifikasi`**: Sistem pemberitahuan internal untuk memfasilitasi komunikasi antara Disnaker dengan sekolah anggota.

---

## 👥 Alur Kerja Pengguna & Fungsionalitas
### 1. Akun Disnaker (Admin / `role = disnaker`)
* **Halaman Login**: Menggunakan akun admin default `disnaker` / `admin123`.
* **Dashboard Disnaker**:
  - Melihat ringkasan data statistik kelulusan dari seluruh SMK anggota (total sekolah terdaftar, sebaran status negeri/swasta, sebaran pekerjaan lulusan, total perusahaan mitra).
  - Melihat diagram visual rekapitulasi data tahunan.
* **Verifikasi Akun (`/verifikasi_akun`)**:
  - Memverifikasi akun baru yang didaftarkan oleh sekolah.
  - Menghubungkan akun user `fbkk` dengan data profil `anggota_fbkk` yang terdaftar.
  - Memutuskan hubungan akun sekolah jika diperlukan.
* **Manajemen Informasi/Pengumuman (`/dashboard_informasi`)**:
  - Membuat pengumuman baru (termasuk upload lampiran file/gambar).
  - Mengaktifkan/menonaktifkan publikasi pengumuman agar muncul di halaman depan.
  - Menghapus pengumuman.
* **Mengirim Notifikasi (`/notifikasi/kirim`)**:
  - Mengirim notifikasi tertarget kepada sekolah tertentu dengan tipe `'umum'`, `'permintaan_data'`, atau `'permintaan_laporan'`.
* **Manajemen Galeri (`/galeri`)**:
  - Menambahkan galeri kegiatan tahunan baru dengan mengunggah beberapa foto sekaligus.
  - Menambahkan atau menghapus foto tertentu di dalam galeri kegiatan yang sudah ada.

### 2. Akun Sekolah Anggota (BKK SMK / `role = fbkk`)
* **Pendaftaran Akun (`/register`)**: Sekolah membuat akun baru. Akun baru ini berstatus belum aktif dan memerlukan verifikasi serta penautan profil oleh pihak Disnaker.
* **Dashboard Anggota (`/dashboard_anggota`)**:
  - Setelah diverifikasi, pengguna dapat mengisi data tahunan kelulusan sekolahnya (jumlah lulusan, kerja, kuliah, wirausaha, belum bekerja, jumlah mitra, dan kepemilikan izin BKK).
* **Unggah Laporan (`/upload_laporan`)**:
  - Mengunggah file laporan sekolah (berupa PDF, DOCX, XLSX, PNG, JPG) lengkap dengan judul dan deskripsinya.
  - Melihat riwayat laporan yang telah diunggah dan menghapus laporan milik sendiri.
* **Kotak Masuk Notifikasi (`/notifikasi`)**:
  - Menerima pesan penting atau instruksi dari Disnaker (seperti permintaan pengisian data tahunan atau laporan bulanan).
  - Pesan yang dibaca akan otomatis berubah status menjadi `read` dan menyembunyikan lencana notifikasi baru di header.

---

## 🖼️ Tampilan Antarmuka (Screenshots)

Berikut adalah beberapa tampilan halaman utama dan fungsionalitas dari aplikasi Website FBKK:

````carousel
![Dashboard Disnaker (Admin)](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\disnaker_dashboard_1782152248799.png)
<!-- slide -->
![Verifikasi Akun Sekolah](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\account_verification_1782152271698.png)
<!-- slide -->
![Kirim Notifikasi ke Anggota](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\send_notification_1782152283690.png)
<!-- slide -->
![Dashboard Sekolah Anggota (BKK SMK)](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\member_dashboard_1782152330326.png)
<!-- slide -->
![Halaman Unggah Laporan Sekolah](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\upload_report_1782152565394.png)
<!-- slide -->
![Kotak Masuk Notifikasi Sekolah](C:\Users\LENOVO\.gemini\antigravity\brain\12465a28-89f7-4954-8974-81f5851c6797\notification_inbox_1782152585807.png)
````
