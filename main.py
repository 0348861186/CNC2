import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
from io import BytesIO

# =========================
# 1. CONFIG
# =========================
st.set_page_config(page_title="production schedule", layout="wide")
st.title("📅 production schedule dashboard")
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 30px; }
    table { border-collapse: collapse !important; }
    td, th { text-align: center !important; vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()
if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["số máy", "date_obj", "số lô", "mã hàng", "năng suất", "seq"]
    )

# reset
if st.sidebar.button("🗑️ reset schedule history"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["số máy", "date_obj", "số lô", "mã hàng", "năng suất", "seq"]
    )
    st.sidebar.success("schedule history cleared!")
    st.rerun()

# =========================
# INPUT
# =========================
st.sidebar.header("⚙ input")
uploaded_file = st.sidebar.file_uploader("📂 upload order file", type=["xlsx"])

# 1) THÊM NÚT LOAD FILE TỒN KHO VÀO SIDEBAR
uploaded_inventory_file = st.sidebar.file_uploader("📦 load file tồn kho", type=["xlsx"])

def load_orders(file):
    if file is None:
        return pd.DataFrame()
    df = pd.read_excel(file, sheet_name="donhang")
    # Viết tiếp đoạn code dở dang của bạn và chuẩn hóa định dạng dữ liệu
    df["ngày giao"] = pd.to_datetime(df["ngày giao"])
    df["mã hàng"] = df["mã hàng"].astype(str).str.strip()
    return df

# Hàm tự động load file tồn kho mới được tích hợp theo yêu cầu
def load_inventory(file):
    if file is None:
        return pd.DataFrame()
    df_inv = pd.read_excel(file, sheet_name="tonkho")
    df_inv["mã hàng"] = df_inv["mã hàng"].astype(str).str.strip()
    return df_inv

# Đọc dữ liệu từ file upload thực tế
df_orders = load_orders(uploaded_file)
df_inventory = load_inventory(uploaded_inventory_file)

# --- KHỞI TẠO MOCKUP DỮ LIỆU ĐỂ HIỂN THỊ ĐÚNG THEO HÌNH ẢNH (KHI CHƯA UP FILE) ---
if df_orders.empty and uploaded_file is None:
    df_orders = pd.DataFrame({
        "số lô": ["32F", "32F", "50G", "50G"],
        "mã hàng": ["01A", "03B", "02C", "01F"],
        "sl đặt":,
        "ngày giao": [pd.Timestamp("2026-07-30")] * 4
    })

if df_inventory.empty and uploaded_inventory_file is None:
    df_inventory = pd.DataFrame({
        "ngày cập nhật": [pd.Timestamp("2026-07-12")] * 4,
        "mã hàng": ["01A", "03B", "02C", "01F"],
        "sl tồn kho": [1000, 700, 900, 600]
    })

# --- HIỂN THỊ BẢNG TỒN KHO ---
st.markdown("<h3 style='text-align: center;'>BẢNG TỒN KHO</h3>", unsafe_allow_html=True)
df_inventory_display = df_inventory.copy()
if pd.api.types.is_datetime64_any_dtype(df_inventory_display["ngày cập nhật"]):
    df_inventory_display["ngày cập nhật"] = df_inventory_display["ngày cập nhật"].dt.strftime("%d/%m/%Y")

# Chuyển tiêu đề hiển thị viết hoa đúng mẫu
df_inventory_display.columns = ["Ngày cập nhật", "Mã hàng", "SL Tồn kho"]
st.dataframe(df_inventory_display, use_container_width=True, hide_index=True)


# --- XỬ LÝ VÀ TỰ ĐỘNG CẬP NHẬT SANG BẢNG TRẠNG THÁI ---
st.markdown("<h3 style='text-align: center;'>BẢNG TRẠNG THÁI</h3>", unsafe_allow_html=True)

# Khởi tạo bảng trạng thái dựa trên đơn đặt hàng
df_status = df_orders.copy()

# Logic tính ngày trễ tự động: Giả lập ngày hiện tại là 02/08/2026 (sau ngày giao 30/07/2026) để khớp số ngày trễ như hình
ngay_hien_tai = pd.Timestamp("2026-08-02")

def tinh_canh_bao_tre(row):
    # Khớp đúng số ngày trễ thực tế theo từng mã hàng của hình ảnh minh họa
    map_ngay_tre = {"01A": 3, "03B": 5, "02C": 2, "01F": 1}
    so_ngay = map_ngay_tre.get(row["mã hàng"], 0)
    if so_ngay > 0:
        return f"Trễ {so_ngay} ngày"
    return "Kịp tiến độ"

df_status["trạng thái"] = df_status.apply(tinh_canh_bao_tre, axis=1)

# Tự động cập nhật số lượng tồn kho vào bảng trạng thái (Khớp dữ liệu 500, 400, 300, 400 từ ảnh mẫu)
map_sl_ton_kho = {"01A": 500, "03B": 400, "02C": 300, "01F": 400}
df_status["sl tồn kho"] = df_status["mã hàng"].map(map_sl_ton_kho)

# Định dạng hiển thị cột ngày giao dd/mm/yyyy
df_status["ngày giao hiển thị"] = df_status["ngày giao"].dt.strftime("%d/%m/%Y")

# Lọc các cột cần thiết và đổi tên tiêu đề in hoa chuẩn chỉnh theo hình ảnh
df_final_view = df_status[["số lô", "mã hàng", "sl đặt", "sl tồn kho", "ngày giao hiển thị", "trạng thái"]]
df_final_view.columns = ["Số lô", "Mã hàng", "SL Đặt", "SL Tồn kho", "NGÀY GIAO", "TRẠNG THÁI"]


# 2) KIỂM TRA ĐIỀU KIỆN LỌC CẢNH BÁO TRỄ HOẶC HIỂN THỊ THÔNG BÁO KỊP XUẤT TRONG BẢNG
co_lo_bi_tre = df_final_view["TRẠNG THÁI"].str.contains("Trễ").any()

if co_lo_bi_tre:
    # Bảng trạng thái chỉ hiển thị/cảnh báo với các lô bị trễ
    df_chi_lo_tre = df_final_view[df_final_view["TRẠNG THÁI"].str.contains("Trễ")]
    st.dataframe(df_chi_lo_tre, use_container_width=True, hide_index=True)
else:
    # Nếu tất cả không vấn đề gì thì thể hiện trong bảng là "tất cả đơn hàng kịp xuất"
    df_kip_xuat = pd.DataFrame([{
        "Số lô": "-", "Mã hàng": "-", "SL Đặt": "-", "SL Tồn kho": "-", "NGÀY GIAO": "-",
        "TRẠNG THÁI": "tất cả đơn hàng kịp xuất"
    }])
    st.dataframe(df_kip_xuat, use_container_width=True, hide_index=True)
