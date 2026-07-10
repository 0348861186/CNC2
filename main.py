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
st.title("📅 PRODUCTION SCHEDULE DASHBOARD")

st.markdown("""
<style>
.block-container { padding-top: 1rem; }
h1 { font-size: 30px; }

/* TABLE STYLE GLOBAL */
table {
    border-collapse: collapse !important;
}
td, th {
    text-align: center !important;
    vertical-align: middle !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()

if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )

if "df_inventory" not in st.session_state:
    st.session_state.df_inventory = pd.DataFrame()

if "df_orders_combined" not in st.session_state:
    st.session_state.df_orders_combined = pd.DataFrame()

# RESET
if st.sidebar.button("🗑️ Reset Lịch Sử Schedule"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.session_state.df_inventory = pd.DataFrame()
    st.session_state.df_orders_combined = pd.DataFrame()
    st.sidebar.success("Đã xóa lịch cũ và dữ liệu!")
    st.rerun()

# =========================
# 2. INPUT & SIDEBAR
# =========================
st.sidebar.header("⚙ INPUT")

# 1. Nút load file đơn hàng
uploaded_orders = st.sidebar.file_uploader("📂 Load đơn hàng (csv, xlsx)", type=['csv', 'xlsx'])
if uploaded_orders is not None:
    try:
        if uploaded_orders.name.endswith('.csv'):
            new_df = pd.read_csv(uploaded_orders)
        else:
            new_df = pd.read_excel(uploaded_orders)
        
        # Tổng hợp file đơn hàng (cập nhật từ 2 lần trở lên sẽ gộp lại)
        if st.session_state.df_orders_combined.empty:
            st.session_state.df_orders_combined = new_df
        else:
            st.session_state.df_orders_combined = pd.concat([st.session_state.df_orders_combined, new_df], ignore_index=True)
        st.sidebar.success("Đã load và gộp đơn hàng thành công!")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file đơn hàng: {e}")

# 2. Nút load file tồn kho
uploaded_inventory = st.sidebar.file_uploader("📂 Load file tồn kho (csv, xlsx)", type=['csv', 'xlsx'])
if uploaded_inventory is not None:
    try:
        if uploaded_inventory.name.endswith('.csv'):
            st.session_state.df_inventory = pd.read_csv(uploaded_inventory)
        else:
            st.session_state.df_inventory = pd.read_excel(uploaded_inventory)
        st.sidebar.success("Đã cập nhật tồn kho thành công!")
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file tồn kho: {e}")

# =========================
# 3. DASHBOARD DISPLAYS
# =========================

# Hiển thị bảng phụ 1: Tóm tắt trạng thái đơn hàng (Ví dụ: Trễ / OK)
st.subheader("📋 Bảng phụ: Trạng thái các lô hàng (Tồn kho/Đơn hàng)")

# Ví dụ logic tính toán giả định cho trạng thái (có thể điều chỉnh hàm cho phù hợp nghiệp vụ)
if not st.session_state.df_orders_combined.empty and not st.session_state.df_inventory.empty:
    # --- Giả lập tính toán đơn giản: Nơi kiểm tra lượng tồn kho và tiến độ ---
    temp_df = st.session_state.df_orders_combined.copy()
    
    # Giả lập cột 'Trạng thái' cho từng lô dựa trên năng suất và tồn kho
    conditions = [
        temp_df.index % 2 == 0, # Giả lập điều kiện trễ
        temp_df.index % 2 != 0  # Giả lập điều kiện ok
    ]
    choices = ['Lô đang trễ', 'Lô OK']
    temp_df['Trạng thái'] = np.select(conditions, choices, default='Chưa xác định')
    
    st.dataframe(temp_df[['Mã Hàng', 'SỐ LÔ', 'Trạng thái']])

elif not st.session_state.df_orders_combined.empty:
    st.info("Vui lòng tải thêm file TỒN KHO lên hệ thống để tính toán trạng thái.")
else:
    st.info("Hãy tải file Đơn Hàng và Tồn Kho lên thanh menu (Sidebar) bên trái để bắt đầu.")

# Hiển thị bảng phụ 2: Tổng hợp tất cả đơn hàng đã load
if not st.session_state.df_orders_combined.empty:
    st.subheader("📦 Bảng tổng hợp tất cả đơn hàng đã tải lên")
    st.dataframe(st.session_state.df_orders_combined)

# Hiển thị bảng phụ 3: Dữ liệu tồn kho hiện tại
if not st.session_state.df_inventory.empty:
    st.subheader("📊 Dữ liệu Tồn kho hiện tại")
    st.dataframe(st.session_state.df_inventory)
