-- Migrasi fitur lengkap (galeri multi-foto, dll.)
-- Jalankan: python migrate_database.py

USE fbkk_db;

CREATE TABLE IF NOT EXISTS foto_galeri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    galeri_id INT NOT NULL,
    foto_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (galeri_id) REFERENCES galeri(id) ON DELETE CASCADE
);

-- Tambah kolom tahun jika belum ada (abaikan error jika sudah ada)
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'fbkk_db' AND TABLE_NAME = 'galeri' AND COLUMN_NAME = 'tahun'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE galeri ADD COLUMN tahun INT NULL AFTER judul',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Migrasi data lama: file_path -> foto_galeri
SET @has_file_path = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'fbkk_db' AND TABLE_NAME = 'galeri' AND COLUMN_NAME = 'file_path'
);
SET @sql2 = IF(@has_file_path > 0,
    'INSERT INTO foto_galeri (galeri_id, foto_path)
     SELECT id, file_path FROM galeri WHERE file_path IS NOT NULL AND file_path != ''''
     AND id NOT IN (SELECT galeri_id FROM foto_galeri)',
    'SELECT 1');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

SET @sql3 = IF(@has_file_path > 0,
    'UPDATE galeri SET tahun = YEAR(created_at) WHERE tahun IS NULL',
    'SELECT 1');
PREPARE stmt3 FROM @sql3;
EXECUTE stmt3;
DEALLOCATE PREPARE stmt3;

SET @sql4 = IF(@has_file_path > 0,
    'ALTER TABLE galeri DROP COLUMN file_path',
    'SELECT 1');
PREPARE stmt4 FROM @sql4;
EXECUTE stmt4;
DEALLOCATE PREPARE stmt4;

UPDATE galeri SET tahun = YEAR(created_at) WHERE tahun IS NULL;
ALTER TABLE galeri MODIFY tahun INT NOT NULL;
