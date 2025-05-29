import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta

# === SETUP ===
st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# === DATABASE ===
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

# Buat tabel users
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

# === SESSION ===
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
                st.experimental_rerun()
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
                c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)", (new_user, new_pass))
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

# === MENU KHUSUS ADMIN ===
if st.session_state.is_admin:
    st.header("📊 Admin Dashboard")

    df = pd.read_sql_query("SELECT * FROM kirim", conn)
    if df.empty:
        st.info("Belum ada data.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"])

        st.subheader("Semua Rekapan")
        st.dataframe(df)

        st.subheader("Total Pendapatan Keseluruhan")
        st.metric("Total (Rp)", f"{df['Pendapatan'].sum():,.0f}")

        st.subheader("Pendapatan per Karyawan")
        st.bar_chart(df.groupby("user")["Pendapatan"].sum())

        st.subheader("Dashboard Mingguan")
        minggu_lalu = date.today() - timedelta(days=7)
        df_minggu = df[df["tanggal"] >= pd.to_datetime(minggu_lalu)]
        if not df_minggu.empty:
            chart = df_minggu.groupby(df_minggu["tanggal"].dt.strftime("%d-%m"))["Pendapatan"].sum()
            st.line_chart(chart)

        st.subheader("Dashboard Bulanan")
        df["Bulan"] = df["tanggal"].dt.strftime("%B %Y")
        bulanan = df.groupby("Bulan")["Pendapatan"].sum().reset_index()
        st.bar_chart(bulanan.set_index("Bulan"))

else:
    # === MENU UNTUK USER BIASA ===
    menu = st.sidebar.selectbox("Menu", ["Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan"])

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
                c.execute("""INSERT INTO kirim (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan, user)
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan, st.session_state.username))
                conn.commit()
                st.success("Data berhasil disimpan.")

    elif menu == "Rekap Penjualan":
        st.header("Rekap Penjualan")
        df = pd.read_sql_query("SELECT * FROM kirim WHERE user = ?", conn, params=(st.session_state.username,))
        if df.empty:
            st.info("Belum ada data.")
        else:
            df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
            st.dataframe(df)
            st.subheader(f"Total Pendapatan: Rp {df['Pendapatan'].sum():,.0f}")

    elif menu == "Dashboard":
        st.header("Dashboard Harian")
        hari_ini = date.today()
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

    elif menu == "Laporan Bulanan":
        st.header("Laporan Bulanan")
        bulan = st.selectbox("Pilih Bulan", list(range(1, 13)), format_func=lambda x: f"{x:02}")
        tahun = st.number_input("Tahun", value=date.today().year, step=1)

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
