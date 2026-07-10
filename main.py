import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
from io import BytesIO

# ========================= #
# 1. CONFIG #
# ========================= #
st.set_page_config(page_title="Production Schedule", layout="wide")
st.title("📅 PRODUCTION SCHEDULE DASHBOARD")
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 30px; }
    /* TABLE STYLE GLOBAL */
    table { border-collapse: collapse !important; }
    td, th { text-align: center !important; vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)

# ========================= #
# SESSION STATE #
# ========================= #
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()

if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )

# --- KHỞI TẠO STATE CHO ĐƠN HÀNG TỔNG HỢP VÀ TỒN KHO CẬP NHẬT THEO CẤU TRÚC MỚI ---
if "df_orders_summary" not in st.session_state:
    st.session_state.df_orders_summary = pd.DataFrame(
        columns=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "NGÀY ĐẶT HÀNG", "NĂNG SUẤT", "SL ĐẶT", "TỒN KHO"]
    )

if "uploaded_order_files" not in st.session_state:
    st.session_state.uploaded_order_files = []

if "df_inventory" not in st.session_state:
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])

# RESET
if st.sidebar.button("🗑️ Reset Lịch Sử Schedule & Dữ Liệu"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    # Reset dữ liệu tích lũy và tồn kho hàng ngày
    st.session_state.df_orders_summary = pd.DataFrame(
        columns=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "NGÀY ĐẶT HÀNG", "NĂNG SUẤT", "SL ĐẶT", "TỒN KHO"]
    )
    st.session_state.uploaded_order_files = []
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])
    
    st.sidebar.success("Đã xóa lịch cũ và toàn bộ dữ liệu!")
    st.rerun()

# ========================= #
# 2. INPUT #
# ========================= #
st.sidebar.header("⚙ INPUT")

# Hàm làm sạch dữ liệu khi đọc file
def clean_dataframe(df):
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    return df

# Hàm load đơn hàng gốc
def load_orders(file):
    if file is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(file)
        return clean_dataframe(df)
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file đơn hàng: {e}")
        return pd.DataFrame()

# Hàm đọc file tồn kho thực tế hàng ngày
def load_inventory(file):
    if file is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(file)
        return clean_dataframe(df)
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file tồn kho: {e}")
        return pd.DataFrame()


# Tải file đơn hàng (Sidebar)
uploaded_file = st.sidebar.file_uploader("📂 Load đơn hàng", type=["xlsx"])

# Nút tải file tồn kho hàng ngày (Sidebar)
inventory_file = st.sidebar.file_uploader("📦 Load file tồn kho hàng ngày", type=["xlsx"])


# --- XỬ LÝ GỘP ĐƠN HÀNG KHI UPDATE TỪ 2 LẦN TRỞ LÊN VỚI CẤU TRÚC TIÊU ĐỀ MỚI ---
if uploaded_file is not None:
    if uploaded_file.name not in st.session_state.uploaded_order_files:
        df_new_orders = load_orders(uploaded_file)
        # Các cột bắt buộc cần có theo đúng cấu trúc ảnh mới cung cấp
        required_cols = ["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "NGÀY ĐẶT HÀNG", "NĂNG SUẤT", "SL ĐẶT", "TỒN KHO"]
        
        if all(col in df_new_orders.columns for col in required_cols):
            if st.session_state.df_orders_summary.empty:
                st.session_state.df_orders_summary = df_new_orders[required_cols].copy()
            else:
                # Nối file mới vào file cũ để gộp thành một file duy nhất
                st.session_state.df_orders_summary = pd.concat(
                    [st.session_state.df_orders_summary, df_new_orders[required_cols]], 
                    ignore_index=True
                )
                # Loại bỏ trùng lặp nếu trùng cả SỐ LÔ và MÃ HÀNG (giữ lại dữ liệu mới nhất)
                st.session_state.df_orders_summary.drop_duplicates(subset=["SỐ LÔ", "MÃ HÀNG"], keep="last", inplace=True)
            
            st.session_state.uploaded_order_files.append(uploaded_file.name)
            st.sidebar.success(f"Đã tổng hợp đơn hàng từ: {uploaded_file.name}")
        else:
            st.sidebar.error("Cấu trúc file đơn hàng không khớp! Vui lòng kiểm tra lại các tiêu đề cột.")

# --- XỬ LÝ CẬP NHẬT FILE TỒN KHO HÀNG NGÀY ---
if inventory_file is not None:
    df_inv_data = load_inventory(inventory_file)
    required_inv_cols = ["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"]
    if all(col in df_inv_data.columns for col in required_inv_cols):
        st.session_state.df_inventory = df_inv_data[required_inv_cols].copy()
        st.sidebar.success("Đã cập nhật dữ liệu tồn kho thực tế!")
    else:
        st.sidebar.error("File tồn kho cần có các cột: Ngày cập nhật, MÃ HÀNG, Tồn kho thực tế")


# ========================= #
# 3. DISPLAY BẢNG PHỤ (DASHBOARD) #
# ========================= #
col_left, col_right = st.columns()

with col_left:
    st.subheader("📋 Bảng Đơn Hàng Tổng Hợp Tích Lũy")
    if not st.session_state.df_orders_summary.empty:
        st.dataframe(st.session_state.df_orders_summary, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu đơn hàng gộp.")

with col_right:
    st.subheader("📊 Bảng Phụ: TRẠNG THÁI TỪNG LÔ HÀNG")
    
    if not st.session_state.df_orders_summary.empty:
        # Clone lại dữ liệu từ đơn hàng tổng hợp
        df_status_calc = st.session_state.df_orders_summary.copy()
        
        # Đồng bộ so khớp qua cột 'MÃ HÀNG' với file Tồn Kho Thực Tế
        if not st.session_state.df_inventory.empty:
            df_status_calc = df_status_calc.merge(st.session_state.df_inventory, on="MÃ HÀNG", how="left")
            df_status_calc["NGÀY GIAO"] = pd.to_datetime(df_status_calc["NGÀY GIAO"], errors='coerce')
            df_status_calc["Ngày cập nhật"] = pd.to_datetime(df_status_calc["Ngày cập nhật"], errors='coerce')
        else:
            df_status_calc["Tồn kho thực tế"] = np.nan
            df_status_calc["Ngày cập nhật"] = pd.NaT

        # Logic tính trạng thái: Nếu tồn kho thực tế <= 0, tính độ lệch ngày trễ từ NGÀY GIAO
        def evaluate_row_status(row):
            if pd.isna(row["Tồn kho thực tế"]) or row["Tồn kho thực tế"] <= 0:
                if pd.notna(row["Ngày cập nhật"]) and pd.notna(row["NGÀY GIAO"]):
                    gap_days = (row["Ngày cập nhật"] - row["NGÀY GIAO"]).days
                    if gap_days > 0:
                        return f"trễ {gap_days} ngày"
                return "trễ"
            else:
                return "ok"

        df_status_calc["TRẠNG THÁI"] = df_status_calc.apply(evaluate_row_status, axis=1)
        
        # Tạo bảng hiển thị đúng định dạng cấu trúc phụ: SỐ LÔ, MÃ HÀNG, TRẠNG THÁI
        df_final_view = df_status_calc[["SỐ LÔ", "MÃ HÀNG", "TRẠNG THÁI"]].copy()
        df_final_view.sort_values(by=["SỐ LÔ", "MÃ HÀNG"], inplace=True)

        # Định dạng màu sắc highlight
        def apply_color_mapping(val):
            if "trễ" in str(val).lower():
                return "color: #D32F2F; font-weight: bold; background-color: #FFEBEE;"
            if "ok" in str(val).lower():
                return "color: #388E3C; font-weight: bold; background-color: #E8F5E9;"
            return ""

        st.dataframe(
            df_final_view.style.applymap(apply_color_mapping, subset=["TRẠNG THÁI"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Vui lòng tải lên file đơn hàng để kích hoạt bảng trạng thái tự động.")

st.markdown("---")

# Tiếp tục chạy toàn bộ các đoạn code xử lý ma trận và lịch phân tách phía dưới cũ của bạn...
