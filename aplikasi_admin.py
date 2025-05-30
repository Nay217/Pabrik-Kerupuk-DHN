import streamlit as st 
import pandas as pd
import sqlite3
from datetime import date

# === KONFIGURASI HALAMAN ===
st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# === KONEKSI DATABASE ===
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

# === SETUP TABEL ===
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

# === CEK ADMIN PERTAMA ===
c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
if c.fetchone()[0] == 0:
    st.info("Belum ada admin. User pertama yang mendaftar akan jadi admin otomatis.")

# === SESSION STATE ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# === LOGIN & REGISTRASI ===
menu_auth = st.sidebar.selectbox("Login / Daftar", ["Login", "Daftar"])

if not st.session_state.logged_in:
    if menu_auth == "Login":
        st.subheader("Login")
        username = st.text_input("Nama Pengguna")
        password = st.text_input("Password", type="password")
        if st.button("Masuk"):
            c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = bool(user[2])
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah.")
    else:
        st.subheader("Daftar Akun Baru")
        new_user = st.text_input("Buat Username")
        new_pass = st.text_input("Buat Password", type="password")
        if st.button("Daftar"):
            c.execute("SELECT * FROM users WHERE username = ?", (new_user,))
            if c.fetchone():
                st.error("Username sudah dipakai.")
            else:
                c.execute("SELECT COUNT(*) FROM users")
                user_count = c.fetchone()[0]
                is_admin = 1 if user_count == 0 else 0
                c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                          (new_user, new_pass, is_admin))
                conn.commit()
                st.success("Akun berhasil dibuat. Silakan login.")
    st.stop()

# === LOGOUT ===
st.sidebar.markdown(f"**Login sebagai:** {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()

# === MENU UTAMA ===
menu = st.sidebar.selectbox("Menu", ["Rekap Penjualan", "Dashboard", "Laporan Bulanan", "Gaji Karyawan" ])

# === MENU ADMIN KHUSUS ===
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
        else:
            st.info("Tidak ada user biasa untuk dipromosikan.")

# === MENU: Rekap Penjualan ===
elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan")
    if st.session_state.is_admin:
        df = pd.read_sql("SELECT * FROM kirim", conn)
    else:
        df = pd.read_sql("SELECT * FROM kirim WHERE user = ?", conn, params=(st.session_state.username,))
    if df.empty:
        st.info("Belum ada data.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan: Rp {df['Pendapatan'].sum():,.0f}")

# === MENU: Dashboard Harian ===
elif menu == "Dashboard":
    st.header("Dashboard Harian")
    hari_ini = date.today()
    if st.session_state.is_admin:
        df = pd.read_sql("SELECT * FROM kirim WHERE tanggal = ?", conn, params=(hari_ini,))
    else:
        df = pd.read_sql("SELECT * FROM kirim WHERE tanggal = ? AND user = ?", conn,
                         params=(hari_ini, st.session_state.username))
    if df.empty:
        st.info("Belum ada data hari ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Pendapatan Hari Ini: Rp {df['Pendapatan'].sum():,.0f}")
        df_chart = df.groupby("warung")["Pendapatan"].sum().reset_index()
        st.bar_chart(df_chart.set_index("warung"))

# === MENU: Laporan Bulanan ===
elif menu == "Laporan Bulanan":
    st.header("Laporan Bulanan")
    bulan = st.selectbox("Pilih Bulan", list(range(1, 13)), format_func=lambda x: f"{x:02}")
    tahun = st.number_input("Tahun", value=date.today().year, step=1)
    if st.session_state.is_admin:
        df = pd.read_sql(
            "SELECT * FROM kirim WHERE strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ?",
            conn, params=(f"{bulan:02}", str(tahun)))
    else:
        df = pd.read_sql(
            "SELECT * FROM kirim WHERE strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ? AND user = ?",
            conn, params=(f"{bulan:02}", str(tahun), st.session_state.username))
    if df.empty:
        st.info("Belum ada data bulan ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan Bulan Ini: Rp {df['Pendapatan'].sum():,.0f}")

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

# === Tutup koneksi DB ===
conn.close()
