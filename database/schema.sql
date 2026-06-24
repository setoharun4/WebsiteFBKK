-- Skema database Website FBKK Jember
-- Jalankan: mysql -u root -p < database/schema.sql

CREATE DATABASE IF NOT EXISTS fbkk_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE fbkk_db;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('fbkk', 'disnaker') NOT NULL DEFAULT 'fbkk',
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anggota_fbkk (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NULL,
    sekolah VARCHAR(255) NOT NULL,
    alamat VARCHAR(500) NOT NULL,
    kecamatan VARCHAR(100) NOT NULL,
    status ENUM('Negeri', 'Swasta') NOT NULL DEFAULT 'Negeri',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_user) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS data_tahunan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_anggota_fbkk INT NOT NULL,
    tahun INT NOT NULL,
    jumlah_lulusan INT NOT NULL DEFAULT 0,
    lanjut_bekerja INT NOT NULL DEFAULT 0,
    kuliah INT NOT NULL DEFAULT 0,
    wirausaha INT NOT NULL DEFAULT 0,
    belum_bekerja INT NOT NULL DEFAULT 0,
    jumlah_mitra INT NOT NULL DEFAULT 0,
    tanda_daftar_bkk TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_anggota_tahun (id_anggota_fbkk, tahun),
    FOREIGN KEY (id_anggota_fbkk) REFERENCES anggota_fbkk(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS laporan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_anggota_fbkk INT NOT NULL,
    judul VARCHAR(255) NOT NULL,
    deskripsi TEXT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_anggota_fbkk) REFERENCES anggota_fbkk(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS informasi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    judul VARCHAR(255) NOT NULL,
    deskripsi TEXT NOT NULL,
    file_path VARCHAR(500) NULL,
    is_published TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS galeri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    judul VARCHAR(255) NOT NULL,
    tahun INT NOT NULL,
    deskripsi TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS foto_galeri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    galeri_id INT NOT NULL,
    foto_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (galeri_id) REFERENCES galeri(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifikasi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dari_user_id INT NOT NULL,
    ke_user_id INT NOT NULL,
    judul VARCHAR(255) NOT NULL,
    isi TEXT NOT NULL,
    jenis ENUM('umum', 'permintaan_data', 'permintaan_laporan') NOT NULL DEFAULT 'umum',
    link_url VARCHAR(500) NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dari_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (ke_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notifikasi_penerima (ke_user_id, is_read)
);
