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
st.set_page_config(page_title="Production Schedule", layout="wide")
st.title("📅 Production Schedule Dashboard")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 30px; }
    table { border-collapse: collapse !important; }
    td, th { text-align: center !important; vertical-align: middle !important; }
    .status-delayed { color: red; font-weight: bold; }
    .status-ok { color: green; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE INITIALIZATION
# =========================
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()

if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["Số máy", "date_obj", "Số lô", "Mã hàng", "Năng suất", "Seq"]
    )

# Lưu trữ dữ liệu tồn kho hàng ngày
if "df_inventory" not in st.session_state:
    st.session_state.df_inventory = pd.DataFrame(columns=["Mã hàng", "Số lô", "Số lượng tồn"])

# Lưu trữ dữ liệu lịch sử đơn hàng (để cộng dồn/tổng hợp)
if "df_orders_history" not in st.session_state:
    st.session_state.df_orders_history = pd.DataFrame(columns=["Số lô", "Mã hàng", "Số lượng đặt", "Ngày giao"])

# Đếm số lần cập nhật đơn hàng
if "order_update_count" not in st.session_state:
    st.session_state.order_update_count = 0

# Sidebar Reset
if st.sidebar.button("🗑️ Reset Toàn Bộ Hệ Thống"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["Số máy", "date_obj", "Số lô", "Mã hàng", "Năng suất", "Seq"]
    )
    st.session_state.df_inventory = pd.DataFrame(columns=["Mã hàng", "Số lô", "Số lượng tồn"])
    st.session_state.df_orders_history = pd.DataFrame(columns=["Số lô", "Mã hàng", "Số lượng đặt", "Ngày giao"])
    st.session_state.order_update_count = 0
    st.sidebar.success("Đã xóa toàn bộ lịch sử!")
    st.rerun()

# =========================
# 2. INPUT SECTION (SIDEBAR & DASHBOARD)
# =========================
st.sidebar.header("📥 Tải Lên Dữ Liệu Hệ Thống")

# YÊU CẦU 1: Nút load file tồn kho cập nhật hàng ngày
inventory_file = st.sidebar.file_uploader("Chọn file Tồn kho hàng ngày (Excel/CSV)", type=["xlsx", "csv"], key="inv_upload")
if inventory_file:
    try:
        if inventory_file.name.endswith(".xlsx"):
            df_inv_raw = pd.read_excel(inventory_file)
        else:
            df_inv_raw = pd.read_csv(inventory_file)
        
        # Chuẩn hóa tên cột viết hoa chữ cái đầu theo logic gốc
        df_inv_raw.columns = [col.strip().title() for col in df_inv_raw.columns]
        
        # Lưu vào session state
        st.session_state.df_inventory = df_inv_raw
        st.sidebar.success("✅ Đã cập nhật file tồn kho!")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file tồn kho: {e}")

# YÊU CẦU 2: Tải và tổng hợp file đơn hàng
order_file = st.sidebar.file_uploader("Chọn file Đơn hàng mới (Excel/CSV)", type=["xlsx", "csv"], key="order_upload")
if order_file:
    try:
        if order_file.name.endswith(".xlsx"):
            df_order_raw = pd.read_excel(order_file)
        else:
            df_order_raw = pd.read_csv(order_file)
            
        df_order_raw.columns = [col.strip().title() for col in df_order_raw.columns]
        
        # Nút xác nhận lưu để tránh trigger tự động reload của Streamlit khi đổi dữ liệu
        if st.sidebar.button("💾 Xác nhận nạp đơn hàng"):
            st.session_state.order_update_count += 1
            
            if st.session_state.order_update_count == 1:
                # Lần đầu tiên: Ghi đè mới
                st.session_state.df_orders_history = df_order_raw
            else:
                # Từ lần thứ 2 trở lên: Gộp chung và tổng hợp cộng dồn số lượng đặt
                combined_df = pd.concat([st.session_state.df_orders_history, df_order_raw], ignore_index=True)
                
                # Group by theo Số lô và Mã hàng để cộng dồn
                # Chọn Ngày giao sớm nhất hoặc muộn nhất tùy logic doanh nghiệp (ở đây lấy Min)
                st.session_state.df_orders_history = combined_df.groupby(["Số Lô", "Mã Hàng"], as_index=False).agg({
                    "Số Lượng Đặt": "sum",
                    "Ngày Giao": "first"
                })
            st.sidebar.success(f"✅ Đã nạp thành công! (Lần cập nhật: {st.session_state.order_update_count})")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file đơn hàng: {e}")


# =========================
# 3. PROCESSING & LOGIC TRẠNG THÁI LÔ
# =========================
# Giả lập hoặc tính toán ma trận lịch trình (Giữ logic gốc của bạn ở đây)
# Dưới đây là phần tính toán trạng thái phụ thuộc vào Tồn kho và Đơn hàng tổng hợp

df_status_summary = pd.DataFrame()

if not st.session_state.df_orders_history.empty:
    # Gộp bảng đơn hàng đã tổng hợp với bảng tồn kho hàng ngày để so sánh lượng hàng
    df_status_summary = st.session_state.df_orders_history.copy()
    
    if not st.session_state.df_inventory.empty:
        # Merge dựa trên Số lô và Mã hàng
        df_status_summary = pd.merge(
            df_status_summary, 
            st.session_state.df_inventory[["Số Lô", "Mã Hàng", "Số Lượng Tồn"]], 
            on=["Số Lô", "Mã Hàng"], 
            how="left"
        )
        # Điền 0 nếu lô đó không xuất hiện trong file tồn kho (chưa nhập kho)
        df_status_summary["Số Lượng Tồn"] = df_status_summary["Số Lượng Tồn"].fillna(0)
    else:
        df_status_summary["Số Lượng Tồn"] = 0

    # Logic tính toán trạng thái trễ: Nếu lượng tồn kho hiện tại nhỏ hơn lượng đơn hàng yêu cầu -> Trễ
    def check_status(row):
        if row["Số Lượng Tồn"] >= row["Số Lượng Đặt"]:
            return "Lô OK"
        else:
            return "Lô Trễ"

    df_status_summary["Trạng Thái"] = df_status_summary.apply(check_status, axis=1)


# =========================
# 4. DISPLAY LAYOUT ON DASHBOARD
# =========================
col_main, col_sub = st.columns([7, 3])

with col_main:
    st.subheader("📊 Tiến Độ / Ma Trận Sản Xuất Chính")
    if not st.session_state.df_matrix_schedule.empty:
        st.dataframe(st.session_state.df_matrix_schedule, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu tiến độ sản xuất chính. Vui lòng chạy logic lên lịch sản xuất gốc.")

with col_sub:
    st.subheader("📋 Bảng Phụ: Trạng Thái Từng Lô")
    
    # Hiển thị số lần đã cập nhật file đơn hàng để kiểm soát thông tin
    st.metric("Số lần đã gộp đơn hàng", f"{st.session_state.order_update_count} lần")
    
    if not df_status_summary.empty:
        # Định dạng màu sắc hiển thị cho bảng phụ trực quan
        def style_status_rows(val):
            if val == "Lô Trễ":
                return "background-color: #ffcccc; color: red; font-weight: bold;"
            elif val == "Lô OK":
                return "background-color: #ccffcc; color: green; font-weight: bold;"
            return ""

        styled_df = df_status_summary.style.applymap(style_status_rows, subset=["Trạng Thái"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("Vui lòng tải lên file Đơn hàng & Tồn kho để theo dõi trạng thái lô.")

# Hiển thị nhanh bảng Tồn kho hiện tại dưới chân trang nếu cần kiểm tra
if st.checkbox("🔍 Xem nhanh dữ liệu tồn kho hiện tại"):
    if not st.session_state.df_inventory.empty:
        st.dataframe(st.session_state.df_inventory, use_container_width=True)
    else:
        st.warning("Dữ liệu tồn kho trống.")
