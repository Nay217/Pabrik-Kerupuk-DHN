import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# === DB SETUP ===
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

# Buat tabel user
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)
""")

# Buat tabel kirim
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

# === SESSION STATE ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# === REGISTRASI & LOGIN ===
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
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_user, new_pass))
                conn.commit()
                st.success("Akun berhasil dibuat. Silakan login.")
    st.stop()

# === LOGOUT ===
st.sidebar.markdown(f"**Login sebagai:** {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.experimental_rerun()

# === MENU UTAMA ===
menu = st.sidebar.selectbox("Menu", ["Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan"])
st.title("Dashboard Keuangan Kerupuk")

# === MENU Kirim ===
if menu == "Kirim ke Warung":
    st.header("Input Pengiriman / Titipan")
    tanggal = st.date_input("Tanggal", date.today())
    warung = st.text_input("Nama Warung")
    jumlah_kirim = st.number_input("Jumlah Kerupuk Dikirim", min_value=0)
    jumlah_terjual = st.number_input("Jumlah Terjual", min_value=0)
    harga_satuan = st.number_input("Harga Satuan (Rp)", min_value=0)

    if st.button("Simpan"):
        if not warung:
            st.warning("Nama warung tidak boleh kosong.")
        elif jumlah_terjual > jumlah_kirim:
            st.warning("Jumlah terjual tidak boleh lebih besar dari jumlah kirim.")
        else:
            c.execute("""
                INSERT INTO kirim (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan, user)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan, st.session_state.username))
            conn.commit()
            st.success("Data berhasil disimpan.")

# === MENU Rekap Penjualan ===
elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan")
    if st.session_state.is_admin:
        df = pd.read_sql_query("SELECT * FROM kirim", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM kirim WHERE user = ?", conn, params=(st.session_state.username,))
    if df.empty:
        st.info("Belum ada data.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan: Rp {df['Pendapatan'].sum():,.0f}")

# === MENU Dashboard Harian ===
elif menu == "Dashboard":
    st.header("Dashboard Harian")
    hari_ini = date.today()
    if st.session_state.is_admin:
        df = pd.read_sql_query("SELECT * FROM kirim WHERE tanggal = ?", conn, params=(hari_ini,))
    else:
        df = pd.read_sql_query(
            "SELECT * FROM kirim WHERE tanggal = ? AND user = ?",
            conn, params=(hari_ini, st.session_state.username)
        )
    if df.empty:
        st.info("Belum ada data hari ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Pendapatan Hari Ini: Rp {df['Pendapatan'].sum():,.0f}")
        df_chart = df.groupby("warung")["Pendapatan"].sum().reset_index()
        st.bar_chart(df_chart.set_index("warung"))

# === MENU Laporan Bulanan ===
elif menu == "Laporan Bulanan":
    st.header("Laporan Bulanan")
    bulan = st.selectbox("Pilih Bulan", list(range(1, 13)), format_func=lambda x: f"{x:02}")
    tahun = st.number_input("Tahun", value=date.today().year, step=1)
    if st.session_state.is_admin:
        query = """
            SELECT * FROM kirim
            WHERE strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ?
        """
        df = pd.read_sql_query(query, conn, params=(f"{bulan:02}", str(tahun)))
    else:
        query = """
            SELECT * FROM kirim
            WHERE strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ? AND user = ?
        """
        df = pd.read_sql_query(query, conn, params=(f"{bulan:02}", str(tahun), st.session_state.username))
    if df.empty:
        st.info("Belum ada data bulan ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan Bulan Ini: Rp {df['Pendapatan'].sum():,.0f}")

# === Tutup koneksi ===
conn.close()
