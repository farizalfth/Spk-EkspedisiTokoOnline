from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import pandas as pd
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_terakhir_yang_paling_aman_untuk_semua_role_final'

# --- KONFIGURASI DAN KONEKSI DATABASE ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'db_spk_saw_flask'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# --- DECORATORS UNTUK HAK AKSES ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Anda harus login terlebih dahulu untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_action_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Akses ditolak. Hanya Admin yang dapat melakukan aksi ini.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated_function)

# --- FUNGSI HELPER UNTUK PERHITUNGAN SAW ---
def get_saw_results():
    conn = get_db_connection()
    if not conn: return None
    try:
        df_kriteria = pd.read_sql("SELECT * FROM kriteria", conn)
        bobot = df_kriteria.set_index('nama_kriteria')['bobot'].to_dict()
        tipe = df_kriteria.set_index('nama_kriteria')['tipe'].to_dict()
        df_alternatif = pd.read_sql("SELECT * FROM ekspedisi", conn, index_col='id_ekspedisi')
        if df_alternatif.empty: return None
        df_penilaian = pd.read_sql("SELECT id_ekspedisi, AVG(kualitas) as kualitas, AVG(komunikasi) as komunikasi FROM penilaian GROUP BY id_ekspedisi", conn, index_col='id_ekspedisi')
        df = df_alternatif.join(df_penilaian).fillna(0)
        df = df.rename(columns={'biaya': 'Biaya', 'kecepatan': 'Kecepatan', 'cakupan_wilayah': 'Cakupan Wilayah', 'kualitas': 'Kualitas Pelayanan', 'komunikasi': 'Komunikasi'})
        matriks_r = df.copy()
        for kriteria, jenis in tipe.items():
            if kriteria not in matriks_r.columns or matriks_r[kriteria].sum() == 0: continue
            if jenis.lower() == 'cost':
                min_val = matriks_r[kriteria][matriks_r[kriteria] > 0].min()
                if pd.isna(min_val): continue
                matriks_r[kriteria] = matriks_r[kriteria].apply(lambda x: min_val / x if x > 0 else 0)
            else:
                max_val = matriks_r[kriteria].max()
                if max_val == 0: continue
                matriks_r[kriteria] = matriks_r[kriteria] / max_val
        skor_akhir = pd.DataFrame(index=matriks_r.index)
        skor_akhir['nama'] = df['nama']
        skor_akhir['skor'] = sum(matriks_r[k].fillna(0) * w for k, w in bobot.items() if k in matriks_r.columns)
        skor_akhir = skor_akhir.sort_values(by='skor', ascending=False).reset_index(drop=True)
        skor_akhir['rangking'] = skor_akhir.index + 1
        return skor_akhir
    except Exception as e:
        print(f"Error in SAW calculation: {e}")
        return None
    finally:
        if conn and conn.is_connected(): conn.close()

# --- RUTE PUBLIK & LOGIN ---
@app.route('/')
def index():
    # --- PERUBAHAN UTAMA DI SINI ---
    # Fungsi ini sekarang HANYA menampilkan halaman index.html,
    # tidak peduli status login pengguna.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Logika redirect otomatis juga dihapus dari sini.
    # Ini memungkinkan admin yang sudah login bisa melihat halaman login lagi (jika diperlukan).
    if request.method == 'POST':
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (request.form['username'], request.form['password']))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f'Login berhasil! Selamat datang, {user["username"]}.', 'success')
                return redirect(url_for('dashboard')) # Setelah login, baru arahkan ke dashboard
            else:
                flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/hasil-publik')
def hasil_publik():
    hasil = get_saw_results()
    if hasil is None or hasil.empty:
        flash("Belum ada data yang cukup untuk menampilkan peringkat.", "warning")
    return render_template('hasil_publik.html', hasil=hasil)

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('index')) # Setelah logout, kembali ke halaman landing

# --- RUTE PANEL SETELAH LOGIN (UNTUK SEMUA ROLE) ---
@app.route('/dashboard')
@login_required # Hanya bisa diakses jika sudah login
def dashboard():
    conn = get_db_connection()
    if conn is None: return redirect(url_for('login'))
    cursor = conn.cursor(dictionary=True)
    results = {}
    cursor.execute("SELECT COUNT(*) as count FROM ekspedisi"); results['total_alternatif'] = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM kriteria"); results['total_kriteria'] = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM penilaian"); results['total_penilaian'] = cursor.fetchone()['count']
    cursor.execute("SELECT tipe, COUNT(*) as count FROM kriteria GROUP BY tipe"); tipe_counts = cursor.fetchall()
    results['total_benefit'] = next((item['count'] for item in tipe_counts if item['tipe'] == 'benefit'), 0)
    results['total_cost'] = next((item['count'] for item in tipe_counts if item['tipe'] == 'cost'), 0)
    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html', **results)

# (Sisa kode tidak berubah, semua sudah benar)
@app.route('/alternatif')
@login_required
def alternatif():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ekspedisi ORDER BY id_ekspedisi"); data = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('alternatif.html', alternatif=data)

# Di dalam app.py

@app.route('/kriteria')
@login_required # Semua user yang login bisa lihat halaman ini
def kriteria():
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kriteria")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('kriteria.html', kriteria=data)

@app.route('/kriteria/update', methods=['POST'])
@admin_action_required # Hanya admin yang bisa mengirim data (POST)
def update_kriteria():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        total_bobot = 0
        ids = [key.split('_')[1] for key in request.form if key.startswith('bobot_')]
        for id_kriteria in ids:
            total_bobot += float(request.form[f'bobot_{id_kriteria}'])
        
        # Validasi sederhana, total bobot harus 1
        if abs(total_bobot - 1.0) > 0.001:
            flash(f'Gagal! Total bobot harus tepat 1, bukan {total_bobot}.', 'danger')
            return redirect(url_for('kriteria'))

        for id_kriteria in ids:
            bobot = request.form[f'bobot_{id_kriteria}']
            tipe = request.form[f'tipe_{id_kriteria}']
            cursor.execute("UPDATE kriteria SET bobot = %s, tipe = %s WHERE id_kriteria = %s", (bobot, tipe, id_kriteria))
        
        conn.commit()
        flash('Bobot dan tipe kriteria berhasil diperbarui.', 'success')
    except Exception as e:
        flash(f"Terjadi error: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('kriteria'))

@app.route('/customer')
@login_required
def customer():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer ORDER BY id_customer"); data = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('customer.html', customers=data)

@app.route('/penilaian')
@login_required
def penilaian():
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.id_penilaian, e.nama as nama_ekspedisi, c.nama as nama_customer, p.kualitas, p.komunikasi, p.tanggal FROM penilaian p JOIN ekspedisi e ON p.id_ekspedisi = e.id_ekspedisi JOIN customer c ON p.id_customer = c.id_customer ORDER BY p.tanggal DESC, p.id_penilaian DESC")
    data_penilaian = cursor.fetchall()
    cursor.execute("SELECT id_ekspedisi, nama FROM ekspedisi"); ekspedisi = cursor.fetchall()
    cursor.execute("SELECT id_customer, nama FROM customer"); customers = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('penilaian.html', penilaian=data_penilaian, ekspedisi=ekspedisi, customers=customers)

# Di dalam app.py

@app.route('/hasil')
@login_required
def hasil_perhitungan():
    conn = get_db_connection()
    if not conn:
        return render_template('hasil.html', error="Tidak bisa terhubung ke database.")
        
    try:
        df_kriteria = pd.read_sql("SELECT * FROM kriteria", conn)
        bobot = df_kriteria.set_index('nama_kriteria')['bobot'].to_dict()
        tipe = df_kriteria.set_index('nama_kriteria')['tipe'].to_dict()
        df_alternatif = pd.read_sql("SELECT * FROM ekspedisi", conn, index_col='id_ekspedisi')
        if df_alternatif.empty:
            flash("Tidak ada data alternatif untuk dihitung.", "warning")
            return render_template('hasil.html', error="Data alternatif kosong.")

        df_penilaian = pd.read_sql("SELECT id_ekspedisi, AVG(kualitas) as kualitas, AVG(komunikasi) as komunikasi FROM penilaian GROUP BY id_ekspedisi", conn, index_col='id_ekspedisi')
        df = df_alternatif.join(df_penilaian).fillna(0)
        df = df.rename(columns={'biaya': 'Biaya', 'kecepatan': 'Kecepatan', 'cakupan_wilayah': 'Cakupan Wilayah', 'kualitas': 'Kualitas Pelayanan', 'komunikasi': 'Komunikasi'})
        
        matriks_awal = df[['nama'] + list(bobot.keys())]
        matriks_r = matriks_awal.copy()
        for kriteria, jenis in tipe.items():
            if kriteria not in matriks_r.columns or matriks_r[kriteria].sum() == 0: continue
            if jenis.lower() == 'cost':
                min_val = matriks_r[kriteria][matriks_r[kriteria] > 0].min()
                if pd.isna(min_val): continue
                matriks_r[kriteria] = matriks_r[kriteria].apply(lambda x: min_val / x if x > 0 else 0)
            else:
                max_val = matriks_r[kriteria].max()
                if max_val == 0: continue
                matriks_r[kriteria] = matriks_r[kriteria] / max_val
        
        skor_akhir = pd.DataFrame(index=df.index)
        skor_akhir['nama'] = df['nama']
        skor_akhir['skor'] = sum(matriks_r[k].fillna(0) * w for k, w in bobot.items() if k in matriks_r.columns)
        skor_akhir = skor_akhir.sort_values(by='skor', ascending=False).reset_index(drop=True)
        skor_akhir['rangking'] = skor_akhir.index + 1
        
        # ======================================================
        # KODE BARU VERSI 2.0: MEMBUAT PENJELASAN SUPER DETAIL
        # ======================================================
        penjelasan_perhitungan = []
        matriks_r_sorted = matriks_r.set_index('nama').loc[skor_akhir['nama']].reset_index()

        for index, row in skor_akhir.iterrows():
            nama_alternatif = row['nama']
            formula_symbolic_parts = []
            formula_numeric_parts = []
            
            norm_values = matriks_r_sorted.loc[matriks_r_sorted['nama'] == nama_alternatif].iloc[0]
            
            for kriteria, w in bobot.items():
                kriteria_var_name = kriteria.replace(" ", "") # Hapus spasi untuk nama variabel
                r_val = norm_values.get(kriteria, 0)
                
                # Buat bagian formula simbolik: (R_Biaya x W_Biaya)
                symbolic_part = f"(R<sub>{kriteria_var_name}</sub> × W<sub>{kriteria_var_name}</sub>)"
                formula_symbolic_parts.append(symbolic_part)

                # Buat bagian formula numerik: (0.9286 * 0.10)
                numeric_part = f"({r_val:.4f} * {w:.2f})"
                formula_numeric_parts.append(numeric_part)
            
            # Gabungkan semua bagian menjadi satu string formula lengkap
            formula_symbolic_str = "V = " + " + ".join(formula_symbolic_parts)
            formula_numeric_str = "V = " + " + ".join(formula_numeric_parts)
            
            penjelasan_perhitungan.append({
                'nama': nama_alternatif,
                'skor': row['skor'],
                'rangking': row['rangking'],
                'formula_symbolic': formula_symbolic_str,
                'formula_numeric': formula_numeric_str
            })
        # ======================================================
        # AKHIR KODE BARU
        # ======================================================

        chart_labels = skor_akhir['nama'].tolist()
        chart_scores = skor_akhir['skor'].tolist()

    except Exception as e:
        flash(f'Terjadi error saat melakukan perhitungan: {e}', 'danger')
        return render_template('hasil.html', error=str(e))
    finally:
        if conn and conn.is_connected(): conn.close()

    return render_template('hasil.html', 
                           table_awal=matriks_awal.to_html(classes='table table-bordered table-striped', index=False, float_format='{:,.2f}'.format),
                           table_normalisasi=matriks_r_sorted.to_html(classes='table table-bordered table-striped', index=False, float_format='{:.4f}'.format),
                           table_hasil=skor_akhir[['rangking', 'nama', 'skor']].to_html(classes='table table-bordered table-striped', index=False, float_format='{:.6f}'.format),
                           alternatif_terbaik=skor_akhir.iloc[0],
                           chart_labels=chart_labels,
                           chart_scores=chart_scores,
                           penjelasan_perhitungan=penjelasan_perhitungan,
                           error=None)

# --- RUTE AKSI (CRUD) - HANYA UNTUK ADMIN ---
@app.route('/alternatif/add', methods=['POST'])
@admin_action_required
def add_alternatif():
    # ... (logika tidak berubah)
    return redirect(url_for('alternatif'))

@app.route('/alternatif/edit/<int:id>', methods=['POST'])
@admin_action_required
def edit_alternatif(id):
    # ... (logika tidak berubah)
    return redirect(url_for('alternatif'))

@app.route('/alternatif/delete/<int:id>', methods=['POST'])
@admin_action_required
def delete_alternatif(id):
    # ... (logika tidak berubah)
    return redirect(url_for('alternatif'))

@app.route('/customer/add', methods=['POST'])
@admin_action_required
def add_customer():
    # ... (logika tidak berubah)
    return redirect(url_for('customer'))

@app.route('/customer/edit/<int:id>', methods=['POST'])
@admin_action_required
def edit_customer(id):
    # ... (logika tidak berubah)
    return redirect(url_for('customer'))

@app.route('/customer/delete/<int:id>', methods=['POST'])
@admin_action_required
def delete_customer(id):
    # ... (logika tidak berubah)
    return redirect(url_for('customer'))

@app.route('/penilaian/add', methods=['POST'])
@admin_action_required
def add_penilaian():
    # ... (logika tidak berubah)
    return redirect(url_for('penilaian'))

if __name__ == '__main__':
    app.run(debug=True)