import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# Konfigurasi Streamlit
st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# Koneksi DB
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

# Buat tabel-tabel
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS kirim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal DATE,
    warung TEXT,
    jumlah_kirim INTEGER,
    jumlah_terjual INTEGER,
    harga_satuan INTEGER,
    user TEXT
)
""")
conn.commit()

# Inisialisasi session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False

# Cek admin pertama
c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
if c.fetchone()[0] == 0:
    st.info("Belum ada admin. User pertama yang daftar akan menjadi admin.")

# AUTH
auth_menu = st.sidebar.selectbox("Login / Daftar", ["Login", "Daftar", "Ganti Password"])

if not st.session_state.logged_in:
    if auth_menu == "Login":
        st.subheader("Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Masuk"):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
            user = c.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.is_admin = bool(user[2])
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah.")
    elif auth_menu == "Daftar":
        st.subheader("Buat Akun Baru")
        new_u = st.text_input("Username Baru")
        new_p = st.text_input("Password Baru", type="password")
        if st.button("Daftar"):
            c.execute("SELECT * FROM users WHERE username=?", (new_u,))
            if c.fetchone():
                st.error("Username sudah digunakan.")
            else:
                c.execute("SELECT COUNT(*) FROM users")
                admin_flag = 1 if c.fetchone()[0] == 0 else 0
                c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_u, new_p, admin_flag))
                conn.commit()
                st.success("Akun berhasil dibuat. Silakan login.")
    elif auth_menu == "Ganti Password":
        st.subheader("Ganti Password")
        u = st.text_input("Username")
        old_p = st.text_input("Password Lama", type="password")
        new_p = st.text_input("Password Baru", type="password")
        if st.button("Update Password"):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, old_p))
            if c.fetchone():
                c.execute("UPDATE users SET password=? WHERE username=?", (new_p, u))
                conn.commit()
                st.success("Password berhasil diperbarui.")
            else:
                st.error("Username atau password lama salah.")
    st.stop()

# Menu utama
st.sidebar.markdown(f"**Login sebagai:** {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()

menu = st.sidebar.selectbox("Menu", [
    "Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan", "Gaji Karyawan"
])

# Admin tools
if st.session_state.is_admin:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 Kelola User")
    if st.sidebar.checkbox("Kelola Hak Akses"):
        st.subheader("Manajemen User")
        df_users = pd.read_sql("SELECT username, is_admin FROM users", conn)
        st.dataframe(df_users)
        non_admins = df_users[df_users["is_admin"] == 0]["username"].tolist()
        if non_admins:
            promote_user = st.selectbox("Pilih user untuk jadi admin", non_admins)
            if st.button("Jadikan Admin"):
                c.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (promote_user,))
                conn.commit()
                st.success(f"{promote_user} sekarang admin!")
                st.rerun()

# Menu: Kirim
if menu == "Kirim ke Warung":
    st.header("Input Pengiriman")
    tgl = st.date_input("Tanggal", date.today())
    warung = st.text_input("Nama Warung")
    kirim = st.number_input("Jumlah Dikirim", min_value=0)
    jual = st.number_input("Jumlah Terjual", min_value=0)
    harga = st.number_input("Harga Satuan (Rp)", min_value=0)
    if st.button("Simpan"):
        if not warung:
            st.warning("Nama warung wajib diisi.")
        elif jual > kirim:
            st.warning("Jumlah terjual tidak boleh lebih besar dari jumlah kirim.")
        else:
            c.execute("INSERT INTO kirim (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan, user) VALUES (?, ?, ?, ?, ?, ?)",
                      (tgl, warung, kirim, jual, harga, st.session_state.username))
            conn.commit()
            st.success("Data disimpan!")

# Menu: Rekap
elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan")
    filter_user = st.selectbox("Filter berdasarkan User", ["Semua"] + list(pd.read_sql("SELECT DISTINCT user FROM kirim", conn)["user"])) if st.session_state.is_admin else st.session_state.username
    filter_warung = st.text_input("Filter Nama Warung (opsional)")
    query = "SELECT * FROM kirim"
    params = []

    if filter_user != "Semua":
        query += " WHERE user = ?"
        params.append(filter_user)
    if filter_warung:
        query += " AND warung LIKE ?" if "WHERE" in query else " WHERE warung LIKE ?"
        params.append(f"%{filter_warung}%")

    df = pd.read_sql_query(query, conn, params=params)
    if df.empty:
        st.info("Tidak ada data.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        st.dataframe(df)
        st.subheader(f"Total Pendapatan: Rp {df['Pendapatan'].sum():,.0f}")
        if st.download_button("Ekspor ke Excel", df.to_csv(index=False).encode(), "rekap.csv", "text/csv"):
            st.success("Berhasil diekspor.")

# Menu: Dashboard
elif menu == "Dashboard":
    st.header("Dashboard Hari Ini")
    today = date.today()
    q = "SELECT * FROM kirim WHERE tanggal = ?"
    p = [today]
    if not st.session_state.is_admin:
        q += " AND user = ?"
        p.append(st.session_state.username)
    df = pd.read_sql_query(q, conn, params=p)
    if df.empty:
        st.info("Belum ada data hari ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        st.dataframe(df)
        st.subheader(f"Total Hari Ini: Rp {df['Pendapatan'].sum():,.0f}")
        st.bar_chart(df.groupby("warung")["Pendapatan"].sum())

# Menu: Laporan Bulanan
elif menu == "Laporan Bulanan":
    st.header("Laporan Bulanan")
    bulan = st.selectbox("Pilih Bulan", range(1, 13))
    tahun = st.number_input("Tahun", value=date.today().year)
    user_filter = "" if st.session_state.is_admin else f"AND user = '{st.session_state.username}'"
    query = f"""
        SELECT * FROM kirim
        WHERE strftime('%m', tanggal) = '{bulan:02}' AND strftime('%Y', tanggal) = '{int(tahun)}'
        {user_filter}
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        st.info("Tidak ada data.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        st.dataframe(df)
        st.subheader(f"Total Pendapatan Bulan Ini: Rp {df['Pendapatan'].sum():,.0f}")
        if st.download_button("Ekspor Excel", df.to_csv(index=False).encode(), "laporan_bulanan.csv", "text/csv"):
            st.success("Berhasil diekspor.")

# Menu: Gaji
elif menu == "Gaji Karyawan":
    st.header("Perhitungan Gaji Karyawan")
    gaji_per_kerupuk = st.number_input("Upah per kerupuk terjual (Rp)", min_value=0, value=500)
    df = pd.read_sql("SELECT user, SUM(jumlah_terjual) as total_terjual FROM kirim GROUP BY user", conn)
    if df.empty:
        st.info("Belum ada data.")
    else:
        df["Gaji"] = df["total_terjual"] * gaji_per_kerupuk
        st.dataframe(df)
        st.subheader(f"Total Gaji Dibayarkan: Rp {df['Gaji'].sum():,.0f}")
        if st.download_button("Ekspor Gaji", df.to_csv(index=False).encode(), "gaji_karyawan.csv", "text/csv"):
            st.success("Data gaji diekspor.")

# Tutup DB
conn.close()
