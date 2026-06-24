from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pymysql
import uuid
import os
import ssl
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from contextlib import contextmanager
import time

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(_BASE_DIR, 'templates'),
    static_folder=os.path.join(_BASE_DIR, 'static'),
)

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'fbkk_db')
    DB_SSL = os.environ.get('DB_SSL', 'false').lower() in ('true', '1', 'yes')
    UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get('VERCEL') else os.path.join(_BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'}
    TEMPLATES_AUTO_RELOAD = True

app.config.from_object(Config)

log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler('app.log'))
except (OSError, PermissionError):
    pass  # Skip file logging on cloud platforms with read-only filesystems

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

@app.context_processor
def inject_template_helpers():
    """Helper variabel global untuk template."""
    from datetime import datetime
    unread_notifikasi = 0
    if session.get('user_id') and session.get('role') == 'fbkk':
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM notifikasi WHERE ke_user_id = %s AND is_read = 0",
                    (session['user_id'],),
                )
                unread_notifikasi = cursor.fetchone()['cnt']
        except Exception:
            unread_notifikasi = 0

    return {
        'csrf_token': lambda: '',
        'current_year': datetime.now().year,
        'current_endpoint': request.endpoint,
        'unread_notifikasi': unread_notifikasi,
    }

app.jinja_env.globals['csrf_token'] = lambda: ''

@contextmanager
def get_db_connection():
    """Context manager for database connections with proper error handling"""
    conn = None
    try:
        connect_args = {
            'host': app.config['DB_HOST'],
            'port': app.config['DB_PORT'],
            'user': app.config['DB_USER'],
            'password': app.config['DB_PASSWORD'],
            'database': app.config['DB_NAME'],
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False,
        }
        if app.config.get('DB_SSL'):
            connect_args['ssl'] = {'ca': None}  # Use system CA for TiDB Cloud
            connect_args['ssl_verify_identity'] = True
        conn = pymysql.connect(**connect_args)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def login_required(role=None):
    """Decorator to require login and optionally specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_image_to_galeri_folder(file_storage):
    """Simpan file gambar ke static/img/galeri, return path relatif."""
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[-1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    galeri_dir = '/tmp/galeri' if os.environ.get('VERCEL') else os.path.join(_BASE_DIR, 'static', 'img', 'galeri')
    os.makedirs(galeri_dir, exist_ok=True)
    filepath = os.path.join(galeri_dir, unique_filename)
    file_storage.save(filepath)
    return f"img/galeri/{unique_filename}"

def get_all_galeri(cursor):
    cursor.execute("""
        SELECT g.id, g.judul, g.tahun, g.deskripsi, MIN(f.foto_path) AS cover
        FROM galeri g
        LEFT JOIN foto_galeri f ON g.id = f.galeri_id
        GROUP BY g.id, g.judul, g.tahun, g.deskripsi, g.created_at
        ORDER BY g.tahun DESC, g.created_at DESC
    """)
    return cursor.fetchall()

def get_galeri_by_tahun(cursor, tahun):
    cursor.execute("""
        SELECT g.id, g.judul, g.tahun, g.deskripsi, MIN(f.foto_path) AS cover
        FROM galeri g
        LEFT JOIN foto_galeri f ON g.id = f.galeri_id
        WHERE g.tahun = %s
        GROUP BY g.id, g.judul, g.tahun, g.deskripsi, g.created_at
        ORDER BY g.created_at DESC
    """, (tahun,))
    return cursor.fetchall()

def get_all_tahun_galeri(cursor):
    cursor.execute("SELECT DISTINCT tahun FROM galeri ORDER BY tahun DESC")
    return [row['tahun'] for row in cursor.fetchall()]

def get_foto_by_galeri_id(cursor, galeri_id):
    cursor.execute("SELECT id, foto_path FROM foto_galeri WHERE galeri_id = %s ORDER BY id ASC", (galeri_id,))
    return cursor.fetchall()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([username, password, confirm_password]):
                return render_template('register.html', error="Semua field wajib diisi!")
            
            if len(username) < 3:
                return render_template('register.html', error="Username minimal 3 karakter!")
            
            if len(password) < 6:
                return render_template('register.html', error="Password minimal 6 karakter!")
            
            if password != confirm_password:
                return render_template('register.html', error="Password dan Konfirmasi Password tidak cocok!")
            
            hashed_password = generate_password_hash(password)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check existing user
                cursor.execute('SELECT user_id FROM users WHERE username = %s', (username,))
                if cursor.fetchone():
                    return render_template('register.html', error="Username sudah digunakan!")
                
                # Insert new user
                cursor.execute(
                    'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                    (username, hashed_password, 'fbkk')
                )
                conn.commit()
                
                logger.info(f"New user registered: {username}")
                return redirect(url_for('login'))
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error="Terjadi kesalahan sistem!")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', error="Username dan password wajib diisi!")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, username, password, role FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session.permanent = True
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    
                    logger.info(f"User logged in: {username}")
                    
                    # Redirect based on role
                    if user['role'] == 'fbkk':
                        return redirect(url_for('dashboard_anggota'))
                    elif user['role'] == 'disnaker':
                        return redirect(url_for('dashboard_disnaker'))
                else:
                    return render_template('login.html', error="Username atau Password salah!")
                    
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return render_template('login.html', error="Terjadi kesalahan sistem!")
    
    return render_template('login.html')

@app.route('/forgot_password')
def forgot_password():
    return render_template('login.html', error="Fitur lupa password belum tersedia. Hubungi admin Disnaker.")

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    logger.info(f"User logged out: {username}")
    return redirect(url_for('login'))

@app.route('/')
def home():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get school statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_sekolah,
                    SUM(CASE WHEN status = 'Swasta' THEN 1 ELSE 0 END) AS swasta,
                    SUM(CASE WHEN status = 'Negeri' THEN 1 ELSE 0 END) AS negeri
                FROM anggota_fbkk
            """)
            sekolah_data = cursor.fetchone()

            # Get graduate data by year
            cursor.execute("""
                SELECT 
                    dt.tahun,
                    SUM(dt.lanjut_bekerja) AS kerja,
                    SUM(dt.kuliah) AS kuliah,
                    SUM(dt.wirausaha) AS wirausaha,
                    SUM(dt.belum_bekerja) AS belum_kerja,
                    SUM(dt.lanjut_bekerja + dt.kuliah + dt.wirausaha + dt.belum_bekerja) AS total_per_tahun,
                    COUNT(DISTINCT dt.id_anggota_fbkk) AS jumlah_sekolah
                FROM data_tahunan dt
                GROUP BY dt.tahun
                ORDER BY dt.tahun DESC
            """)
            lulusan_data = cursor.fetchall()

            # Get total graduates
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(lanjut_bekerja + kuliah + wirausaha + belum_bekerja), 0) AS total_lulusan
                FROM data_tahunan
            """)
            total_lulusan = cursor.fetchone()['total_lulusan']

            # Get published information
            cursor.execute("""
                SELECT id, judul, deskripsi, file_path, created_at 
                FROM informasi 
                WHERE is_published = 1 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            informasi = cursor.fetchall()

            return render_template(
                'home.html', 
                sekolah_data=sekolah_data, 
                lulusan_data=lulusan_data, 
                total_lulusan=total_lulusan,
                informasi=informasi
            )
            
    except Exception as e:
        logger.error(f"Home page error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat halaman")

@app.route('/profil')
def profil():
    try:
        search_query = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "id")
        
        # Whitelist allowed sort columns
        allowed_sort = {"id": "id", "sekolah": "sekolah", "kecamatan": "kecamatan"}
        sort_column = allowed_sort.get(sort_by, "id")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL injection
            sql = f"SELECT id, sekolah, alamat, kecamatan FROM anggota_fbkk WHERE sekolah LIKE %s ORDER BY {sort_column} ASC"
            cursor.execute(sql, (f"%{search_query}%",))
            anggota_list = cursor.fetchall()
        
        return render_template("profil.html", anggota_list=anggota_list)
        
    except Exception as e:
        logger.error(f"Profil page error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat profil")

@app.route("/get_anggota")
def get_anggota():
    try:
        search_query = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "id")
        
        allowed_sort = {"id": "id", "sekolah": "sekolah", "kecamatan": "kecamatan"}
        sort_column = allowed_sort.get(sort_by, "id")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = f"SELECT id, sekolah, alamat, kecamatan FROM anggota_fbkk WHERE sekolah LIKE %s ORDER BY {sort_column} ASC"
            cursor.execute(sql, (f"%{search_query}%",))
            anggota_list = cursor.fetchall()

        return jsonify({"success": True, "data": anggota_list})
        
    except Exception as e:
        logger.error(f"Get anggota API error: {str(e)}")
        return jsonify({"success": False, "error": "Terjadi kesalahan sistem"}), 500

@app.route('/get_data_tahunan/<int:id_anggota>', methods=['GET'])
def get_data_tahunan(id_anggota):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.sekolah, d.tahun,
                       d.lanjut_bekerja AS kerja,
                       d.kuliah,
                       d.wirausaha,
                       IFNULL(d.belum_bekerja, 0) AS belum_bekerja,
                       (IFNULL(d.lanjut_bekerja, 0) + IFNULL(d.kuliah, 0) +
                        IFNULL(d.wirausaha, 0) + IFNULL(d.belum_bekerja, 0)) AS total
                FROM data_tahunan d
                JOIN anggota_fbkk a ON d.id_anggota_fbkk = a.id
                WHERE d.id_anggota_fbkk = %s
                ORDER BY d.tahun DESC
            """, (id_anggota,))
            data_tahunan = cursor.fetchall()

        if not data_tahunan:
            return jsonify({"success": True, "data": [], "message": "Belum ada data", "sekolah": None})

        return jsonify({"success": True, "data": data_tahunan, "sekolah": data_tahunan[0]["sekolah"]})
    except Exception as e:
        logger.error(f"Get data tahunan error: {str(e)}")
        return jsonify({"success": False, "error": "Terjadi kesalahan sistem"}), 500

@app.route('/dashboard_anggota')
@login_required(role='fbkk')
def dashboard_anggota():
    try:
        user_id = session['user_id']
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get member data
            cursor.execute("SELECT * FROM anggota_fbkk WHERE id_user = %s", (user_id,))
            anggota = cursor.fetchone()
            
            if not anggota:
                return render_template('dashboard_anggota.html', anggota=None, data_tahunan=[], pending_verification=True)
            
            # Get yearly data
            cursor.execute("""
                SELECT * FROM data_tahunan 
                WHERE id_anggota_fbkk = %s 
                ORDER BY tahun DESC 
            """, (anggota['id'],))
            data_tahunan = cursor.fetchall()

        return render_template('dashboard_anggota.html', anggota=anggota, data_tahunan=data_tahunan)
        
    except Exception as e:
        logger.error(f"Dashboard anggota error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat dashboard")

@app.route('/simpan_data_tahunan', methods=['POST'])
@login_required(role='fbkk')
def simpan_data_tahunan():
    try:
        # Validate and sanitize input
        required_fields = ['tahun', 'jumlah_lulusan', 'lanjut_bekerja', 'kuliah', 'wirausaha', 'belum_bekerja', 'jumlah_mitra']
        data = {}
        
        for field in required_fields:
            value = request.form.get(field, '').strip()
            if not value or not value.isdigit():
                return jsonify({"success": False, "error": f"Field {field} harus berupa angka"})
            data[field] = int(value)
        
        # Validate year
        if data['tahun'] < 2000 or data['tahun'] > 2030:
            return jsonify({"success": False, "error": "Tahun tidak valid"})
        
        # Validate total
        total_status = data['lanjut_bekerja'] + data['kuliah'] + data['wirausaha'] + data['belum_bekerja']
        if total_status != data['jumlah_lulusan']:
            return jsonify({"success": False, "error": "Total status lulusan harus sama dengan jumlah lulusan"})
        
        data['tanda_daftar_bkk'] = 'tanda_daftar_bkk' in request.form
        user_id = session['user_id']

        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get anggota ID
            cursor.execute("SELECT id FROM anggota_fbkk WHERE id_user = %s", (user_id,))
            anggota = cursor.fetchone()
            
            if not anggota:
                return jsonify({"success": False, "error": "Data sekolah tidak ditemukan"})

            id_anggota_fbkk = anggota['id']

            # Check existing data
            cursor.execute("""
                SELECT id FROM data_tahunan 
                WHERE id_anggota_fbkk = %s AND tahun = %s
            """, (id_anggota_fbkk, data['tahun']))
            existing_data = cursor.fetchone()

            if existing_data:
                # Update existing data
                cursor.execute("""
                    UPDATE data_tahunan 
                    SET jumlah_lulusan = %s, lanjut_bekerja = %s, kuliah = %s, 
                        wirausaha = %s, belum_bekerja = %s, jumlah_mitra = %s, 
                        tanda_daftar_bkk = %s, updated_at = NOW()
                    WHERE id = %s
                """, (
                    data['jumlah_lulusan'], data['lanjut_bekerja'], data['kuliah'],
                    data['wirausaha'], data['belum_bekerja'], data['jumlah_mitra'],
                    data['tanda_daftar_bkk'], existing_data['id']
                ))
            else:
                # Insert new data
                cursor.execute("""
                    INSERT INTO data_tahunan 
                    (id_anggota_fbkk, tahun, jumlah_lulusan, lanjut_bekerja, kuliah, 
                     wirausaha, belum_bekerja, jumlah_mitra, tanda_daftar_bkk) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_anggota_fbkk, data['tahun'], data['jumlah_lulusan'],
                    data['lanjut_bekerja'], data['kuliah'], data['wirausaha'],
                    data['belum_bekerja'], data['jumlah_mitra'], data['tanda_daftar_bkk']
                ))

            conn.commit()
            logger.info(f"Data tahunan saved for user {user_id}, year {data['tahun']}")
            return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Save data tahunan error: {str(e)}")
        return jsonify({"success": False, "error": "Terjadi kesalahan sistem"})

@app.route('/dashboard_disnaker')
@login_required(role='disnaker')
def dashboard_disnaker():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get school statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_sekolah,
                    SUM(CASE WHEN status = 'Swasta' THEN 1 ELSE 0 END) AS swasta,
                    SUM(CASE WHEN status = 'Negeri' THEN 1 ELSE 0 END) AS negeri
                FROM anggota_fbkk
            """)
            sekolah_data = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    dt.tahun,
                    SUM(dt.lanjut_bekerja) AS kerja,
                    SUM(dt.kuliah) AS kuliah,
                    SUM(dt.wirausaha) AS wirausaha,
                    SUM(dt.belum_bekerja) AS belum_bekerja,
                    SUM(dt.lanjut_bekerja + dt.kuliah + dt.wirausaha + dt.belum_bekerja) AS total_per_tahun,
                    COUNT(DISTINCT dt.id_anggota_fbkk) AS jumlah_sekolah
                FROM data_tahunan dt
                GROUP BY dt.tahun
                ORDER BY dt.tahun DESC
            """)
            lulusan_data = cursor.fetchall()

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(lanjut_bekerja + kuliah + wirausaha + belum_bekerja), 0) AS total_lulusan,
                    COALESCE(SUM(lanjut_bekerja), 0) AS total_kerja,
                    COALESCE(SUM(kuliah), 0) AS total_kuliah,
                    COALESCE(SUM(wirausaha), 0) AS total_wirausaha,
                    COALESCE(SUM(belum_bekerja), 0) AS total_belum_bekerja
                FROM data_tahunan
            """)
            total_lulusan = cursor.fetchone()

            cursor.execute("""
                SELECT COALESCE(SUM(dt.jumlah_mitra), 0) AS total_mitra
                FROM data_tahunan dt
                INNER JOIN (
                    SELECT id_anggota_fbkk, MAX(tahun) AS tahun_terbaru
                    FROM data_tahunan
                    GROUP BY id_anggota_fbkk
                ) latest_data
                ON dt.id_anggota_fbkk = latest_data.id_anggota_fbkk
                   AND dt.tahun = latest_data.tahun_terbaru
            """)
            mitra_data = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) AS total_laporan FROM laporan")
            laporan_data = cursor.fetchone()
            
        return render_template('dashboard_disnaker.html', 
                             sekolah_data=sekolah_data,
                             lulusan_data=lulusan_data,
                             total_lulusan=total_lulusan,
                             mitra_data=mitra_data,
                             laporan_data=laporan_data)
                             
    except Exception as e:
        logger.error(f"Dashboard disnaker error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat dashboard")

@app.route('/galeri', methods=['GET', 'POST'])
def galeri():
    try:
        if request.method == 'POST':
            if session.get('role') != 'disnaker':
                return redirect(url_for('login'))

            judul = request.form.get('judul', '').strip()
            tahun = request.form.get('tahun', '').strip()
            deskripsi = request.form.get('deskripsi', '').strip()
            fotos = request.files.getlist('fotos')

            if not judul or not tahun or not fotos:
                return render_template('error.html', message="Judul, tahun, dan foto wajib diisi")

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO galeri (judul, tahun, deskripsi) VALUES (%s, %s, %s)",
                    (judul, int(tahun), deskripsi),
                )
                galeri_id = cursor.lastrowid

                for foto in fotos:
                    if foto and foto.filename and foto.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        foto_path = save_image_to_galeri_folder(foto)
                        cursor.execute(
                            "INSERT INTO foto_galeri (galeri_id, foto_path) VALUES (%s, %s)",
                            (galeri_id, foto_path),
                        )
                conn.commit()

            return redirect(url_for('galeri'))

        tahun_filter = request.args.get('tahun', '')
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if tahun_filter:
                galeri_list = get_galeri_by_tahun(cursor, tahun_filter)
            else:
                galeri_list = get_all_galeri(cursor)
            tahun_list = get_all_tahun_galeri(cursor)

        return render_template(
            'galeri_admin.html' if session.get('role') == 'disnaker' else 'galeri.html',
            galeri_list=galeri_list,
            tahun_list=tahun_list,
            selected_year=tahun_filter,
            is_admin=session.get('role') == 'disnaker',
        )
    except Exception as e:
        logger.error(f"Galeri error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat galeri")

@app.route('/galeri/<int:galeri_id>/fotos')
def get_foto_kegiatan(galeri_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            fotos = get_foto_by_galeri_id(cursor, galeri_id)

        if session.get('role') == 'disnaker':
            return jsonify([{"id": f["id"], "foto_path": f["foto_path"]} for f in fotos])
        return jsonify([f["foto_path"] for f in fotos])
    except Exception as e:
        logger.error(f"Get foto galeri error: {str(e)}")
        return jsonify([]), 500

@app.route('/galeri/upload_tambahan', methods=['POST'])
@login_required(role='disnaker')
def upload_foto_tambahan():
    try:
        galeri_id = request.form.get('galeri_id')
        foto = request.files.get('foto_tambahan')

        if not galeri_id or not foto or foto.filename == '':
            return jsonify({'success': False, 'error': 'Data tidak lengkap'}), 400

        if not foto.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return jsonify({'success': False, 'error': 'Hanya file gambar'}), 400

        foto_path = save_image_to_galeri_folder(foto)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO foto_galeri (galeri_id, foto_path) VALUES (%s, %s)",
                (galeri_id, foto_path),
            )
            foto_id = cursor.lastrowid
            conn.commit()

        return jsonify({'success': True, 'foto_path': foto_path, 'foto_id': foto_id})
    except Exception as e:
        logger.error(f"Upload foto tambahan error: {str(e)}")
        return jsonify({'success': False, 'error': 'Terjadi kesalahan sistem'}), 500

@app.route('/foto/<int:foto_id>/hapus', methods=['DELETE'])
@login_required(role='disnaker')
def hapus_foto(foto_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT foto_path FROM foto_galeri WHERE id = %s", (foto_id,))
            foto = cursor.fetchone()
            if foto:
                file_path = os.path.join('static', foto['foto_path'])
                if os.path.exists(file_path):
                    os.remove(file_path)
                cursor.execute("DELETE FROM foto_galeri WHERE id = %s", (foto_id,))
                conn.commit()
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Foto tidak ditemukan'}), 404
    except Exception as e:
        logger.error(f"Hapus foto error: {str(e)}")
        return jsonify({'success': False, 'error': 'Terjadi kesalahan sistem'}), 500

@app.route('/galeri/<int:galeri_id>/hapus', methods=['POST'])
@login_required(role='disnaker')
def hapus_galeri_kegiatan(galeri_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT foto_path FROM foto_galeri WHERE galeri_id = %s", (galeri_id,))
            for foto in cursor.fetchall():
                file_path = os.path.join('static', foto['foto_path'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            cursor.execute("DELETE FROM galeri WHERE id = %s", (galeri_id,))
            conn.commit()
        return redirect(url_for('galeri'))
    except Exception as e:
        logger.error(f"Hapus galeri error: {str(e)}")
        return render_template('error.html', message="Gagal menghapus galeri")

@app.route('/upload_laporan', methods=['GET', 'POST'])
@login_required(role='fbkk')
def upload_laporan():
    try:
        user_id = session['user_id']

        if request.method == 'POST':
            judul = request.form.get('judul', '').strip()
            deskripsi = request.form.get('deskripsi', '').strip()
            file = request.files.get('file')

            if not judul or not deskripsi or not file or file.filename == '':
                return render_template('error.html', message="Semua field wajib diisi")

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)

                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM anggota_fbkk WHERE id_user = %s", (user_id,))
                    anggota = cursor.fetchone()
                    if not anggota:
                        return render_template('error.html', message="Data sekolah tidak ditemukan")
                    cursor.execute(
                        "INSERT INTO laporan (id_anggota_fbkk, judul, deskripsi, file_path) VALUES (%s, %s, %s, %s)",
                        (anggota['id'], judul, deskripsi, filename),
                    )
                    conn.commit()
                return redirect(url_for('upload_laporan'))
            return render_template('error.html', message="Format file tidak didukung")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM anggota_fbkk WHERE id_user = %s", (user_id,))
            anggota = cursor.fetchone()
            if not anggota:
                return render_template('error.html', message="Akun belum diverifikasi. Hubungi admin Disnaker.")

            cursor.execute("""
                SELECT * FROM laporan
                WHERE id_anggota_fbkk = %s
                ORDER BY created_at DESC
            """, (anggota['id'],))
            laporan_history = cursor.fetchall()

        return render_template(
            'upload_laporan.html',
            anggota=anggota,
            laporan=laporan_history,
            laporan_history=laporan_history,
        )
    except Exception as e:
        logger.error(f"Upload laporan error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat halaman")

@app.route('/dashboard_laporan')
@login_required(role='disnaker')
def dashboard_laporan():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all reports with school info
            cursor.execute("""
                SELECT l.*, af.sekolah, af.kecamatan
                FROM laporan l
                JOIN anggota_fbkk af ON l.id_anggota_fbkk = af.id
                ORDER BY l.created_at DESC
            """)
            laporan_list = cursor.fetchall()
            
        return render_template('dashboard_laporan.html', laporan_list=laporan_list)
        
    except Exception as e:
        logger.error(f"Dashboard laporan error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat dashboard")

@app.route('/dashboard_history')
@login_required()
def dashboard_history():
    try:
        user_id = session['user_id']
        role = session['role']
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if role == 'fbkk':
                # Get user's school data and reports
                cursor.execute("SELECT id FROM anggota_fbkk WHERE id_user = %s", (user_id,))
                anggota = cursor.fetchone()
                
                if anggota:
                    cursor.execute("""
                        SELECT * FROM laporan 
                        WHERE id_anggota_fbkk = %s 
                        ORDER BY created_at DESC
                    """, (anggota['id'],))
                    laporan_list = cursor.fetchall()
                else:
                    laporan_list = []
            else:
                # Disnaker can see all reports
                cursor.execute("""
                    SELECT l.*, af.sekolah, af.kecamatan
                    FROM laporan l
                    JOIN anggota_fbkk af ON l.id_anggota_fbkk = af.id
                    ORDER BY l.created_at DESC
                """)
                laporan_list = cursor.fetchall()
                
        return render_template('dashboard_history.html', laporan_list=laporan_list)
        
    except Exception as e:
        logger.error(f"Dashboard history error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat history")

@app.route('/dashboard_informasi')
@login_required(role='disnaker')
def dashboard_informasi():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all information
            cursor.execute("""
                SELECT * FROM informasi 
                ORDER BY created_at DESC
            """)
            informasi_list = cursor.fetchall()
            
        return render_template('dashboard_informasi.html', informasi_list=informasi_list, informasi=informasi_list)
        
    except Exception as e:
        logger.error(f"Dashboard informasi error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat dashboard")

@app.route('/upload_informasi', methods=['POST'])
@login_required(role='disnaker')
def upload_informasi():
    try:
        judul = request.form.get('judul', '').strip()
        deskripsi = request.form.get('deskripsi', '').strip()
        file = request.files.get('file')
        file_path = None

        if not judul or not deskripsi:
            return redirect(url_for('dashboard_informasi'))

        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(full_path)
            file_path = f"/static/uploads/{filename}"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO informasi (judul, deskripsi, file_path, is_published) VALUES (%s, %s, %s, 0)",
                (judul, deskripsi, file_path),
            )
            conn.commit()

        return redirect(url_for('dashboard_informasi'))
    except Exception as e:
        logger.error(f"Upload informasi error: {str(e)}")
        return render_template('error.html', message="Gagal mengunggah informasi")

@app.route('/toggle_informasi/<int:info_id>', methods=['POST'])
@login_required(role='disnaker')
def toggle_informasi(info_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_published FROM informasi WHERE id = %s", (info_id,))
            info = cursor.fetchone()
            if info:
                new_status = 0 if info['is_published'] else 1
                cursor.execute("UPDATE informasi SET is_published = %s WHERE id = %s", (new_status, info_id))
                conn.commit()
        return redirect(url_for('dashboard_informasi'))
    except Exception as e:
        logger.error(f"Toggle informasi error: {str(e)}")
        return render_template('error.html', message="Gagal mengubah status informasi")

@app.route('/delete_informasi/<int:info_id>', methods=['POST'])
@login_required(role='disnaker')
def delete_informasi(info_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM informasi WHERE id = %s", (info_id,))
            conn.commit()
        return redirect(url_for('dashboard_informasi'))
    except Exception as e:
        logger.error(f"Delete informasi error: {str(e)}")
        return render_template('error.html', message="Gagal menghapus informasi")

@app.route('/verifikasi_akun')
@login_required(role='disnaker')
def verifikasi_akun():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id, u.username, u.created_at
                FROM users u
                LEFT JOIN anggota_fbkk a ON u.user_id = a.id_user
                WHERE a.id_user IS NULL AND u.role = 'fbkk'
                ORDER BY u.created_at DESC
            """)
            users = cursor.fetchall()

            cursor.execute("""
                SELECT id, sekolah FROM anggota_fbkk
                WHERE id_user IS NULL
                ORDER BY sekolah ASC
            """)
            sekolah = cursor.fetchall()

            cursor.execute("""
                SELECT u.user_id, u.username, u.created_at, a.sekolah, a.id AS anggota_id
                FROM users u
                JOIN anggota_fbkk a ON u.user_id = a.id_user
                WHERE u.role = 'fbkk'
                ORDER BY u.created_at DESC
            """)
            verified_users = cursor.fetchall()

            cursor.execute("""
                SELECT id, sekolah, alamat, kecamatan, status
                FROM anggota_fbkk
                WHERE id_user IS NULL
                ORDER BY sekolah ASC
            """)
            sekolah_kosong = cursor.fetchall()

        return render_template(
            'verifikasi_akun.html',
            users=users,
            sekolah=sekolah,
            verified_users=verified_users,
            sekolah_kosong=sekolah_kosong,
        )
    except Exception as e:
        logger.error(f"Verifikasi akun error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat verifikasi akun")

@app.route('/konfirmasi_verifikasi', methods=['POST'])
@login_required(role='disnaker')
def konfirmasi_verifikasi():
    try:
        user_id = request.form.get('user_id')
        id_sekolah = request.form.get('id_anggota')

        if not user_id or not id_sekolah:
            return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE anggota_fbkk SET id_user = %s
                WHERE id = %s AND id_user IS NULL
            """, (user_id, id_sekolah))
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Sekolah sudah terhubung atau tidak ditemukan'}), 400

            cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = %s", (user_id,))
            conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Konfirmasi verifikasi error: {str(e)}")
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem'}), 500

@app.route('/tambah_sekolah_anggota', methods=['POST'])
@login_required(role='disnaker')
def tambah_sekolah_anggota():
    try:
        sekolah = request.form.get('sekolah', '').strip()
        alamat = request.form.get('alamat', '').strip()
        kecamatan = request.form.get('kecamatan', '').strip()
        status = request.form.get('status', 'Negeri').strip()

        if not sekolah or not alamat or not kecamatan:
            return redirect(url_for('verifikasi_akun'))

        if status not in ('Negeri', 'Swasta'):
            status = 'Negeri'

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO anggota_fbkk (sekolah, alamat, kecamatan, status) VALUES (%s, %s, %s, %s)",
                (sekolah, alamat, kecamatan, status),
            )
            conn.commit()

        return redirect(url_for('verifikasi_akun'))
    except Exception as e:
        logger.error(f"Tambah sekolah anggota error: {str(e)}")
        return render_template('error.html', message="Gagal menambahkan sekolah anggota")

@app.route('/hapus_akun_tidak_verifikasi/<int:user_id>', methods=['POST'])
@login_required(role='disnaker')
def hapus_akun_tidak_verifikasi(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id
                FROM users u
                LEFT JOIN anggota_fbkk a ON u.user_id = a.id_user
                WHERE u.user_id = %s AND u.role = 'fbkk' AND a.id_user IS NULL
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'success': False, 'message': 'Akun tidak ditemukan atau sudah terverifikasi'}), 400

            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Hapus akun tidak verifikasi error: {str(e)}")
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem'}), 500

@app.route('/putus_akun_sekolah', methods=['POST'])
@login_required(role='disnaker')
def putus_akun_sekolah():
    try:
        user_id = request.form.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id
                FROM anggota_fbkk a
                JOIN users u ON u.user_id = a.id_user
                WHERE a.id_user = %s AND u.role = 'fbkk'
            """, (user_id,))
            anggota = cursor.fetchone()

            if not anggota:
                return jsonify({'success': False, 'message': 'Akun tidak terhubung ke sekolah manapun'}), 400

            cursor.execute("UPDATE anggota_fbkk SET id_user = NULL WHERE id = %s", (anggota['id'],))
            cursor.execute("UPDATE users SET is_verified = 0 WHERE user_id = %s", (user_id,))
            conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Putus akun sekolah error: {str(e)}")
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem'}), 500

@app.route('/hapus_laporan/<int:id>', methods=['POST'])
@login_required(role='disnaker')
def hapus_laporan(id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM laporan WHERE id = %s", (id,))
            conn.commit()
        return redirect(url_for('dashboard_laporan'))
    except Exception as e:
        logger.error(f"Hapus laporan error: {str(e)}")
        return render_template('error.html', message="Gagal menghapus laporan")

@app.route('/hapus_laporan_anggota/<int:id>', methods=['POST'])
@login_required(role='fbkk')
def hapus_laporan_anggota(id):
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM anggota_fbkk WHERE id_user = %s", (user_id,))
            anggota = cursor.fetchone()
            if anggota:
                cursor.execute(
                    "DELETE FROM laporan WHERE id = %s AND id_anggota_fbkk = %s",
                    (id, anggota['id']),
                )
                conn.commit()
        return redirect(url_for('upload_laporan'))
    except Exception as e:
        logger.error(f"Hapus laporan anggota error: {str(e)}")
        return render_template('error.html', message="Gagal menghapus laporan")

@app.route('/upload_file', methods=['POST'])
@login_required(role='fbkk')
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Tidak ada file yang dipilih"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "Tidak ada file yang dipilih"})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to prevent filename conflicts
            timestamp = str(int(time.time()))
            filename = f"{timestamp}_{filename}"
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Save to database
            user_id = session['user_id']
            judul = request.form.get('judul', '').strip()
            deskripsi = request.form.get('deskripsi', '').strip()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get anggota ID
                cursor.execute("SELECT id FROM anggota_fbkk WHERE id_user = %s", (user_id,))
                anggota = cursor.fetchone()
                
                if anggota:
                    cursor.execute("""
                        INSERT INTO laporan (id_anggota_fbkk, judul, deskripsi, file_path)
                        VALUES (%s, %s, %s, %s)
                    """, (anggota['id'], judul, deskripsi, filename))
                    conn.commit()
                    
                    return jsonify({"success": True, "message": "File berhasil diupload"})
                else:
                    return jsonify({"success": False, "error": "Data sekolah tidak ditemukan"})
        else:
            return jsonify({"success": False, "error": "Tipe file tidak diizinkan"})
            
    except Exception as e:
        logger.error(f"Upload file error: {str(e)}")
        return jsonify({"success": False, "error": "Terjadi kesalahan sistem"})

def get_verified_fbkk_users(cursor):
    cursor.execute("""
        SELECT u.user_id, u.username, a.sekolah
        FROM users u
        JOIN anggota_fbkk a ON u.user_id = a.id_user
        WHERE u.role = 'fbkk' AND u.is_verified = 1
        ORDER BY a.sekolah ASC
    """)
    return cursor.fetchall()

@app.route('/notifikasi')
@login_required(role='fbkk')
def notifikasi_inbox():
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.*, u.username AS dari_username
                FROM notifikasi n
                JOIN users u ON n.dari_user_id = u.user_id
                WHERE n.ke_user_id = %s
                ORDER BY n.created_at DESC
            """, (user_id,))
            notifikasi_list = cursor.fetchall()

        return render_template('notifikasi_inbox.html', notifikasi_list=notifikasi_list)
    except Exception as e:
        logger.error(f"Notifikasi inbox error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat memuat notifikasi")

@app.route('/notifikasi/<int:notif_id>/baca', methods=['POST'])
@login_required(role='fbkk')
def baca_notifikasi(notif_id):
    try:
        user_id = session['user_id']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notifikasi SET is_read = 1 WHERE id = %s AND ke_user_id = %s",
                (notif_id, user_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Notifikasi tidak ditemukan'}), 404

            cursor.execute("SELECT link_url FROM notifikasi WHERE id = %s", (notif_id,))
            row = cursor.fetchone()

        return jsonify({'success': True, 'link_url': row['link_url'] if row else None})
    except Exception as e:
        logger.error(f"Baca notifikasi error: {str(e)}")
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem'}), 500

@app.route('/notifikasi/kirim', methods=['GET', 'POST'])
@login_required(role='disnaker')
def notifikasi_kirim():
    try:
        if request.method == 'POST':
            ke_user_id = request.form.get('ke_user_id', '').strip()
            judul = request.form.get('judul', '').strip()
            isi = request.form.get('isi', '').strip()
            jenis = request.form.get('jenis', 'umum').strip()

            if not ke_user_id or not judul or not isi:
                return redirect(url_for('notifikasi_kirim'))

            if jenis not in ('umum', 'permintaan_data', 'permintaan_laporan'):
                jenis = 'umum'

            link_map = {
                'permintaan_data': url_for('dashboard_anggota'),
                'permintaan_laporan': url_for('upload_laporan'),
                'umum': None,
            }
            link_url = link_map.get(jenis)

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.user_id
                    FROM users u
                    JOIN anggota_fbkk a ON u.user_id = a.id_user
                    WHERE u.user_id = %s AND u.role = 'fbkk' AND u.is_verified = 1
                """, (ke_user_id,))
                if not cursor.fetchone():
                    return render_template('error.html', message="Penerima tidak valid atau belum terverifikasi")

                cursor.execute("""
                    INSERT INTO notifikasi (dari_user_id, ke_user_id, judul, isi, jenis, link_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (session['user_id'], ke_user_id, judul, isi, jenis, link_url))
                conn.commit()

            return redirect(url_for('notifikasi_kirim'))

        selected_user = request.args.get('user_id', '')
        with get_db_connection() as conn:
            cursor = conn.cursor()
            penerima_list = get_verified_fbkk_users(cursor)
            cursor.execute("""
                SELECT n.*, u.username AS ke_username, a.sekolah
                FROM notifikasi n
                JOIN users u ON n.ke_user_id = u.user_id
                LEFT JOIN anggota_fbkk a ON u.user_id = a.id_user
                WHERE n.dari_user_id = %s
                ORDER BY n.created_at DESC
                LIMIT 50
            """, (session['user_id'],))
            riwayat_kirim = cursor.fetchall()

        return render_template(
            'notifikasi_kirim.html',
            penerima_list=penerima_list,
            riwayat_kirim=riwayat_kirim,
            selected_user=selected_user,
        )
    except Exception as e:
        logger.error(f"Notifikasi kirim error: {str(e)}")
        return render_template('error.html', message="Terjadi kesalahan saat mengirim notifikasi")

# Ensure upload directories exist
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(_BASE_DIR, 'static', 'img', 'galeri'), exist_ok=True)
except Exception:
    pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
