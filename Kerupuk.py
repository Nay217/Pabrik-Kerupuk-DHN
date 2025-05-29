import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")

# === COVER ===
st.image("cover web kerupuk.jpg", use_column_width=True)
st.title("Pabrik Kerupuk DHN 🍘")
st.markdown("---")

# === LOGIN SECTION ===

# Contoh kredensial (dalam praktik lebih baik disimpan di database dan dienkripsi)
USERS = {
    "admin": "1234",
    "aceng": "kerupuk"
}

# Cek login status di session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Form login
if not st.session_state.logged_in:
    st.subheader("Silakan Login")
    username = st.text_input("Nama Pengguna")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.success("Login berhasil!")
        else:
            st.error("Nama pengguna atau password salah.")
    st.stop()  # Hentikan eksekusi jika belum login

# === DATABASE ===
conn = sqlite3.connect("kerupuk.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS kirim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal DATE,
    warung TEXT,
    jumlah_kirim INTEGER,
    jumlah_terjual INTEGER,
    harga_satuan INTEGER
)
""")
conn.commit()

# === MENU UTAMA ===
st.title("Dashboard Keuangan Kerupuk Pak Aceng")
menu = st.sidebar.selectbox("Menu", ["Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan"])

# === MENU: Kirim ke Warung ===
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
                INSERT INTO kirim (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan)
                VALUES (?, ?, ?, ?, ?)
            """, (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan))
            conn.commit()
            st.success("Data pengiriman berhasil disimpan.")

# === MENU: Rekap Penjualan ===
elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan")
    df = pd.read_sql_query("SELECT * FROM kirim", conn)

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
    df = pd.read_sql_query("SELECT * FROM kirim WHERE tanggal = ?", conn, params=(hari_ini,))

    if df.empty:
        st.info("Belum ada data untuk hari ini.")
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

    query = """
        SELECT * FROM kirim
        WHERE strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ?
    """
    df = pd.read_sql_query(query, conn, params=(f"{bulan:02}", str(tahun)))

    if df.empty:
        st.info(f"Belum ada data untuk bulan {bulan:02}/{tahun}.")
    else:
        df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d-%m-%Y")
        st.dataframe(df)
        st.subheader(f"Total Pendapatan Bulan {bulan:02}/{tahun}: Rp {df['Pendapatan'].sum():,.0f}")

# Tutup koneksi database
conn.close()
