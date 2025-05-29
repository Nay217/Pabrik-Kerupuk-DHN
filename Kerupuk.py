import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# === LOGIN SECTION ===
USERS = {
    "admin": "1234",
    "aceng": "kerupuk",
    "ucup": "kerupuk2"
}

# Inisialisasi session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Form login
if not st.session_state.logged_in:
    st.subheader("Silakan Login")
    username = st.text_input("Nama Pengguna")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login berhasil!")
            st.experimental_rerun()
        else:
            st.error("Nama pengguna atau password salah.")
    st.stop()

# === SIDEBAR & LOGOUT ===
st.sidebar.markdown(f"**Login sebagai:** {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.experimental_rerun()

# === DATABASE ===
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

# Cek dan tambahkan kolom user jika belum ada
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
c.execute("PRAGMA table_info(kirim)")
columns = [col[1] for col in c.fetchall()]
if "user" not in columns:
    c.execute("ALTER TABLE kirim ADD COLUMN user TEXT")
    conn.commit()

# === MENU ===
st.title("Dashboard Keuangan Kerupuk")
menu = st.sidebar.selectbox("Menu", ["Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan"])

# === Kirim ===
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
            st.success("Data pengiriman berhasil disimpan.")

# === Rekap ===
elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan")
    if st.session_state.username == "admin":
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

# === Dashboard ===
elif menu == "Dashboard":
    st.header("Dashboard Harian")
    hari_ini = date.today()
    if st.session_state.username == "admin":
        df = pd.read_sql_query("SELECT * FROM kirim WHERE tanggal = ?", conn, params=(hari_ini,))
    else:
        df = pd.read_sql_query(
            "SELECT * FROM kirim WHERE tanggal = ? AND user = ?", conn,
            params=(hari_ini, st.session_state.username)
        )
    if df.empty:
        st.info("Belum ada data untuk hari ini.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Pendapatan Hari Ini: Rp {df['Pendapatan'].sum():,.0f}")
        df_chart = df.groupby("warung")["Pendapatan"].sum().reset_index()
        st.bar_chart(df_chart.set_index("warung"))

# === Bulanan ===
elif menu == "Laporan Bulanan":
    st.header("Laporan Bulanan")
    bulan = st.selectbox("Pilih Bulan", list(range(1, 13)), format_func=lambda x: f"{x:02}")
    tahun = st.number_input("Tahun", value=date.today().year, step=1)
    if st.session_state.username == "admin":
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
        st.info(f"Belum ada data untuk bulan {bulan:02}/{tahun}.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan Bulan {bulan:02}/{tahun}: Rp {df['Pendapatan'].sum():,.0f}")

# === Tutup koneksi DB ===
conn.close()
