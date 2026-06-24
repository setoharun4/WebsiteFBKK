"""Migrasi database ke skema fitur lengkap (tanpa menghapus data)."""
import os
import sys

import pymysql

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "fbkk_db")


def column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (DB_NAME, table, column),
    )
    return cursor.fetchone()["cnt"] > 0


def table_exists(cursor, table):
    cursor.execute("SHOW TABLES LIKE %s", (table,))
    return cursor.fetchone() is not None


def main():
    print(f"Migrasi database {DB_NAME}...")
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        with conn.cursor() as cursor:
            if not table_exists(cursor, "foto_galeri"):
                print("Membuat tabel foto_galeri...")
                cursor.execute("""
                    CREATE TABLE foto_galeri (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        galeri_id INT NOT NULL,
                        foto_path VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (galeri_id) REFERENCES galeri(id) ON DELETE CASCADE
                    )
                """)

            if not column_exists(cursor, "galeri", "tahun"):
                print("Menambah kolom galeri.tahun...")
                cursor.execute("ALTER TABLE galeri ADD COLUMN tahun INT NULL AFTER judul")

            if column_exists(cursor, "galeri", "file_path"):
                print("Memindahkan file_path ke foto_galeri...")
                cursor.execute("SELECT id, file_path, created_at FROM galeri WHERE file_path IS NOT NULL AND file_path != ''")
                for row in cursor.fetchall():
                    cursor.execute(
                        "SELECT id FROM foto_galeri WHERE galeri_id = %s AND foto_path = %s",
                        (row["id"], row["file_path"]),
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO foto_galeri (galeri_id, foto_path) VALUES (%s, %s)",
                            (row["id"], row["file_path"]),
                        )
                    if row.get("created_at"):
                        cursor.execute(
                            "UPDATE galeri SET tahun = %s WHERE id = %s AND (tahun IS NULL OR tahun = 0)",
                            (row["created_at"].year, row["id"]),
                        )
                cursor.execute("ALTER TABLE galeri DROP COLUMN file_path")

            cursor.execute("UPDATE galeri SET tahun = YEAR(created_at) WHERE tahun IS NULL OR tahun = 0")
            cursor.execute("ALTER TABLE galeri MODIFY tahun INT NOT NULL")

            if not table_exists(cursor, "notifikasi"):
                print("Membuat tabel notifikasi...")
                cursor.execute("""
                    CREATE TABLE notifikasi (
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
                    )
                """)

        conn.commit()
        print("Migrasi berhasil.")
    except Exception as exc:
        conn.rollback()
        print(f"Migrasi gagal: {exc}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
