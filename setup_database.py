"""Setup database fbkk_db untuk proyek Website FBKK."""
import os
import sys

import pymysql

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "fbkk_db")


def run_sql_file(cursor, path):
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    statements = []
    current = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []

    for statement in statements:
        cursor.execute(statement)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, "database", "schema.sql")
    seed_path = os.path.join(base_dir, "database", "seed.sql")

    for path in (schema_path, seed_path):
        if not os.path.exists(path):
            print(f"File tidak ditemukan: {path}")
            sys.exit(1)

    print(f"Menghubungkan ke MySQL ({DB_USER}@{DB_HOST})...")

    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
    )

    try:
        with conn.cursor() as cursor:
            print("Menghapus database lama (jika ada)...")
            cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")

            print("Membuat struktur database...")
            run_sql_file(cursor, schema_path)

            print("Mengisi data awal...")
            run_sql_file(cursor, seed_path)

        print("\nDatabase berhasil dibuat!")
        print(f"  Database : {DB_NAME}")
        print("  Akun disnaker : disnaker / admin123")
        print("  Akun fbkk     : smk_demo / demo123")
    except pymysql.err.OperationalError as exc:
        print(f"\nGagal koneksi ke MySQL: {exc}")
        print("Pastikan MySQL/XAMPP sudah berjalan.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
