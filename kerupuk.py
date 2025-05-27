import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Pabrik Kerupuk DHN", layout="centered")

# === Tampilan Awal: Cover Image ===
st.image("cover.jpg", use_column_width=True)
st.title("Pabrik Kerupuk DHN")
st.markdown("---")

# Inisialisasi database
conn = sqlite3.connect("kerupuk.db")
c = conn.cursor()

# Buat tabel jika belum ada
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

st.title("Dashboard Keuangan Kerupuk Pak Aceng")

menu = st.sidebar.selectbox("Menu", ["Kirim ke Warung", "Rekap Penjualan", "Dashboard", "Laporan Bulanan"])

if menu == "Kirim ke Warung":
    st.header("Input Pengiriman / Titipan")
    tanggal = st.date_input("Tanggal", date.today())
    warung = st.text_input("Nama Warung")
    jumlah_kirim = st.number_input("Jumlah Kerupuk Dikirim", min_value=0)
    jumlah_terjual = st.number_input("Jumlah Terjual", min_value=0)
    harga_satuan = st.number_input("Harga Satuan (Rp)", min_value=0)

    if st.button("Simpan"):
        c.execute("INSERT INTO kirim (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan) VALUES (?, ?, ?, ?, ?)",
                  (tanggal, warung, jumlah_kirim, jumlah_terjual, harga_satuan))
        conn.commit()
        st.success("Data pengiriman berhasil disimpan.")

elif menu == "Rekap Penjualan":
    st.header("Rekap Penjualan Otomatis")
    df = pd.read_sql_query("SELECT * FROM kirim", conn)
    df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
    st.dataframe(df)

    total = df["Pendapatan"].sum()
    st.subheader(f"Total Pendapatan: Rp {total:,.0f}")

elif menu == "Dashboard":
    st.header("Dashboard Harian")
    hari_ini = date.today()
    df = pd.read_sql_query("SELECT * FROM kirim WHERE tanggal = ?", conn, params=(hari_ini,))
    df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
    st.dataframe(df)

    total_hari = df["Pendapatan"].sum()
    st.subheader(f"Pendapatan Hari Ini: Rp {total_hari:,.0f}")

elif menu == "Laporan Bulanan":
    st.header("Laporan Bulanan")
    bulan = st.selectbox("Pilih Bulan", list(range(1, 13)))
    tahun = st.number_input("Tahun", value=date.today().year)

    query = f"""
        SELECT * FROM kirim
        WHERE strftime('%m', tanggal) = '{bulan:02}' AND strftime('%Y', tanggal) = '{tahun}'
    """
    df = pd.read_sql_query(query, conn)
    df["Pendapatan"] = df["jumlah_terjual"] * df["harga_satuan"]
    st.dataframe(df)

    st.subheader(f"Total Pendapatan Bulan {bulan}/{tahun}: Rp {df['Pendapatan'].sum():,.0f}")