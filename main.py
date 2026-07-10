import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
from io import BytesIO

# =========================
# 1. CONFIG & STYLE
# =========================
st.set_page_config(page_title="production schedule", layout="wide")
st.title("📅 production schedule dashboard")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 30px; }
    table { border-collapse: collapse !important; width: 100%; }
    td, th { text-align: center !important; vertical-align: middle !important; padding: 8px !important; }
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

# Bộ nhớ lưu trữ dữ liệu Tồn kho (Cập nhật hàng ngày)
if "df_inventory" not in st.session_state:
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])

# Bộ nhớ tích hợp Lịch sử Đơn hàng (Gộp nhiều lần)
if "df_orders_combined" not in st.session_state:
    st.session_state.df_orders_combined = pd.DataFrame(columns=["SỐ LÔ", "MÃ HÀNG", "Ngày giao"])

# Đếm số lần nạp file đơn hàng
if "upload_count" not in st.session_state:
    st.session_state.upload_count = 0

# Nút Reset hệ thống trên Sidebar
if st.sidebar.button("🗑️ reset lịch sử schedule"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["số máy", "date_obj", "số lô", "mã hàng", "năng suất", "seq"]
    )
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])
    st.session_state.df_orders_combined = pd.DataFrame(columns=["SỐ LÔ", "MÃ HÀNG", "Ngày giao"])
    st.session_state.upload_count = 0
    st.sidebar.success("đã xóa lịch cũ!")
    st.rerun()


# =========================
# 2. INPUT & PROCESSING LOGIC
# =========================
st.sidebar.header("📥 TẢI DỮ LIỆU ĐẦU VÀO")

# ---------------------------------------------
# YÊU CẦU 1: Nút tải file Tồn kho hàng ngày
# ---------------------------------------------
inv_file = st.sidebar.file_uploader("Chọn file TỒN KHO hàng ngày", type=["xlsx", "csv"])
if inv_file:
    try:
        if inv_file.name.endswith(".xlsx"):
            df_inv_in = pd.read_excel(inv_file)
        else:
            df_inv_in = pd.read_csv(inv_file)
            
        # Chuẩn hóa chuẩn tên cột theo ảnh mẫu
        df_inv_in.columns = [str(c).strip() for c in df_inv_in.columns]
        
        # Chuyển đổi cột Ngày cập nhật sang định dạng datetime để tính toán
        if "Ngày cập nhật" in df_inv_in.columns:
            df_inv_in["Ngày cập nhật"] = pd.to_datetime(df_inv_in["Ngày cập nhật"], errors='coerce')
            
        st.session_state.df_inventory = df_inv_in
        st.sidebar.success("✅ Đã cập nhật file tồn kho!")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file tồn kho: {e}")

# ---------------------------------------------
# YÊU CẦU 2: Tải và tổng hợp file đơn hàng
# ---------------------------------------------
order_file = st.sidebar.file_uploader("Chọn file ĐƠN HÀNG mới", type=["xlsx", "csv"])
if order_file:
    try:
        if order_file.name.endswith(".xlsx"):
            df_ord_in = pd.read_excel(order_file)
        else:
            df_ord_in = pd.read_csv(order_file)
            
        df_ord_in.columns = [str(c).strip() for c in df_ord_in.columns]
        
        if "Ngày giao" in df_ord_in.columns:
            df_ord_in["Ngày giao"] = pd.to_datetime(df_ord_in["Ngày giao"], errors='coerce')

        if st.sidebar.button("💾 Xác nhận gộp đơn hàng"):
            st.session_state.upload_count += 1
            
            if st.session_state.upload_count == 1:
                st.session_state.df_orders_combined = df_ord_in
            else:
                # Gộp chung file cũ và file mới tải lên
                df_merged = pd.concat([st.session_state.df_orders_combined, df_ord_in], ignore_index=True)
                
                # Loại bỏ trùng lặp, giữ lại ngày giao sớm nhất của lô/mã hàng đó
                st.session_state.df_orders_combined = df_merged.groupby(["SỐ LÔ", "MÃ HÀNG"], as_index=False).agg({
                    "Ngày giao": "min"
                })
            st.sidebar.success(f"✅ Đã gộp thành công! (Lần cập nhật: {st.session_state.upload_count})")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file đơn hàng: {e}")


# ---------------------------------------------
# LOGIC TÍNH TRẠNG THÁI TRỄ (THEO NGÀY CẬP NHẬT)
# ---------------------------------------------
df_status_display = pd.DataFrame()

if not st.session_state.df_orders_combined.empty:
    # Lấy thông tin đơn hàng gốc làm nền bảng phụ
    df_status_display = st.session_state.df_orders_combined[["SỐ LÔ", "MÃ HÀNG", "Ngày giao"]].copy()
    
    # Kết nối dữ liệu với file tồn kho mới nhất thông qua MÃ HÀNG
    if not st.session_state.df_inventory.empty:
        df_status_display = pd.merge(
            df_status_display, 
            st.session_state.df_inventory[["MÃ HÀNG", "Ngày cập nhật", "Tồn kho thực tế"]], 
            on="MÃ HÀNG", 
            how="left"
        )
    else:
        df_status_display["Ngày cập nhật"] = pd.NaT
        df_status_display["Tồn kho thực tế"] = 0

    # Hàm tính số ngày trễ dựa trên mốc thời gian thực tế
    def compute_delay_status(row):
        # Nếu không có ngày cập nhật kho hoặc không có ngày giao, mặc định theo dõi tiếp
        if pd.isna(row["Ngày giao"]) or pd.isna(row["Ngày cập nhật"]):
            return "chưa xác định"
            
        # Tính khoảng lệch ngày: Ngày cập nhật kho thực tế trừ đi hạn Ngày giao đơn hàng
        delta_days = (row["Ngày cập nhật"] - row["Ngày giao"]).days
        
        if delta_days > 0:
            return f"trễ {delta_days} ngày"
        else:
            return "ok"

    df_status_display["TRẠNG THÁI"] = df_status_display.apply(compute_delay_status, axis=1)
    
    # Sắp xếp lại thứ tự cột hiển thị giống như giao diện mong muốn của bạn
    df_status_display = df_status_display[["SỐ LÔ", "MÃ HÀNG", "TRẠNG THÁI"]]


# =========================
# 3. DISPLAY ON DASHBOARD
# =========================
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📊 Tiến Độ Lịch Trình Sản Xuất (Chính)")
    if not st.session_state.df_matrix_schedule.empty:
        st.dataframe(st.session_state.df_matrix_schedule, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu ma trận lịch trình gốc.")

with col_right:
    st.subheader("📋 TRẠNG THÁI TỪNG LÔ (Bảng Phụ)")
    
    # Hiển thị trạng thái gộp file
    if st.session_state.upload_count >= 2:
        st.info(f"🔄 Đang hiển thị dữ liệu tổng hợp từ {st.session_state.upload_count} lần cập nhật đơn hàng.")
    
    if not df_status_display.empty:
        # Hàm tô màu cảnh báo trực quan cho ô trạng thái
        def highlight_status(val):
            if "trễ" in str(val):
                return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
            elif val == "ok":
                return "background-color: #ccffcc; color: #006600; font-weight: bold;"
            return ""

        # Gộp nhóm hiển thị (Merge cells trực quan) theo SỐ LÔ giống thiết kế của bạn
        df_sorted = df_status_display.sort_values(by=["SỐ LÔ", "MÃ HÀNG"])
        styled_table = df_sorted.style.applymap(highlight_status, subset=["TRẠNG THÁI"])
        
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
    else:
        st.warning("Vui lòng tải lên cả file đơn hàng và file tồn kho để tính toán trạng thái.")
