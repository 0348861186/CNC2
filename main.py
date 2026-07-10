import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ========================= #
# 1. CONFIG & STYLE #
# ========================= #
st.set_page_config(page_title="Production Schedule", layout="wide")
st.title("📅 PRODUCTION SCHEDULE DASHBOARD")
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 30px; }
    table { border-collapse: collapse !important; width: 100%; }
    td, th { text-align: center !important; vertical-align: middle !important; padding: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ========================= #
# 2. SESSION STATE #
# ========================= #
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()

# Lưu trữ tổng hợp dữ liệu đơn hàng (Gộp từ nhiều lần upload)
if "df_orders_summary" not in st.session_state:
    st.session_state.df_orders_summary = pd.DataFrame(columns=["SỐ LÔ", "MÃ HÀNG", "NGÀY CẦN GIAO"])

# Lưu danh sách tên file đơn hàng đã upload để tránh gộp trùng
if "uploaded_order_files" not in st.session_state:
    st.session_state.uploaded_order_files = []

# Lưu trữ dữ liệu tồn kho cập nhật hàng ngày
if "df_inventory" not in st.session_state:
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])

if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )

# NÚT RESET TOÀN BỘ HỆ THỐNG
if st.sidebar.button("🗑️ Reset Toàn Bộ Dữ Liệu"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_orders_summary = pd.DataFrame(columns=["SỐ LÔ", "MÃ HÀNG", "NGÀY CẦN GIAO"])
    st.session_state.uploaded_order_files = []
    st.session_state.df_inventory = pd.DataFrame(columns=["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"])
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.sidebar.success("Đã xóa toàn bộ dữ liệu lịch sử!")
    st.rerun()

# ========================= #
# 3. INPUT (SIDEBAR) #
# ========================= #
st.sidebar.header("⚙ INPUT DATA")

# Hàm chuẩn hóa dữ liệu khi đọc file Excel
def read_and_clean_excel(file):
    try:
        df = pd.read_excel(file)
        # Loại bỏ khoảng trắng thừa trong tên cột
        df.columns = [str(c).strip() for c in df.columns]
        # Loại bỏ khoảng trắng thừa trong các ô dữ liệu chuỗi
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return pd.DataFrame()

# Upload File Đơn Hàng
uploaded_file = st.sidebar.file_uploader("📂 Load file đơn hàng (Yêu cầu cột: SỐ LÔ, MÃ HÀNG, NGÀY CẦN GIAO)", type=["xlsx"])
if uploaded_file is not None:
    if uploaded_file.name not in st.session_state.uploaded_order_files:
        df_new_orders = read_and_clean_excel(uploaded_file)
        
        # Kiểm tra xem có đúng định dạng cột không
        required_order_cols = ["SỐ LÔ", "MÃ HÀNG", "NGÀY CẦN GIAO"]
        if all(col in df_new_orders.columns for col in required_order_cols):
            # Tiến hành gộp file
            st.session_state.df_orders_summary = pd.concat(
                [st.session_state.df_orders_summary, df_new_orders[required_order_cols]], 
                ignore_index=True
            ).drop_duplicates(subset=["SỐ LÔ", "MÃ HÀNG"], keep="last")
            
            st.session_state.uploaded_order_files.append(uploaded_file.name)
            st.sidebar.success(f" Đã gộp đơn hàng từ: {uploaded_file.name}")
        else:
            st.sidebar.error("File đơn hàng thiếu cột! Yêu cầu: SỐ LÔ, MÃ HÀNG, NGÀY CẦN GIAO")

# Upload File Tồn Kho Hàng Ngày
inventory_file = st.sidebar.file_uploader("📦 Load file tồn kho hàng ngày (Yêu cầu cột: Ngày cập nhật, MÃ HÀNG, Tồn kho thực tế)", type=["xlsx"])
if inventory_file is not None:
    df_inv_data = read_and_clean_excel(inventory_file)
    required_inv_cols = ["Ngày cập nhật", "MÃ HÀNG", "Tồn kho thực tế"]
    
    if all(col in df_inv_data.columns for col in required_inv_cols):
        st.session_state.df_inventory = df_inv_data[required_inv_cols]
        st.sidebar.success(" Cập nhật file Tồn Kho thành công!")
    else:
        st.sidebar.error("File tồn kho thiếu cột! Yêu cầu: Ngày cập nhật, MÃ HÀNG, Tồn kho thực tế")


# ========================= #
# 4. LOGIC TÍNH TRẠNG THÁI & HIỂN THỊ #
# ========================= #
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Dữ Liệu Gốc / File Tồn Kho Hiện Tại")
    if not st.session_state.df_inventory.empty:
        st.write("**Bảng tồn kho thực tế:**")
        st.dataframe(st.session_state.df_inventory, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu tồn kho.")
        
    if not st.session_state.df_orders_summary.empty:
        st.write("**Bảng tổng hợp đơn hàng tích lũy:**")
        st.dataframe(st.session_state.df_orders_summary, use_container_width=True, hide_index=True)

with col2:
    st.subheader("📊 BẢNG TRẠNG THÁI THEO LÔ (DASHBOARD)")
    
    if not st.session_state.df_orders_summary.empty:
        # Bắt đầu từ bảng đơn hàng tổng hợp
        df_dashboard = st.session_state.df_orders_summary.copy()
        
        # Link với bảng tồn kho thông qua cột MÃ HÀNG
        if not st.session_state.df_inventory.empty:
            df_dashboard = df_dashboard.merge(st.session_state.df_inventory, on="MÃ HÀNG", how="left")
            # Chuyển đổi ngày để tính toán khoảng chênh lệch trễ ngày
            df_dashboard["NGÀY CẦN GIAO"] = pd.to_datetime(df_dashboard["NGÀY CẦN GIAO"], errors='coerce')
            df_dashboard["Ngày cập nhật"] = pd.to_datetime(df_dashboard["Ngày cập nhật"], errors='coerce')
        else:
            df_dashboard["Tồn kho thực tế"] = np.nan
            df_dashboard["Ngày cập nhật"] = pd.NaT

        # Hàm xử lý tính toán trạng thái động theo từng dòng hàng
        def calculate_status(row):
            # Nếu không tìm thấy mã hàng trong file tồn kho hoặc tồn kho thực tế bằng 0/thiếu
            if pd.isna(row["Tồn kho thực tế"]) or row["Tồn kho thực tế"] <= 0:
                # Tính số ngày trễ dựa trên ngày cập nhật tồn kho so với ngày cần giao dự kiến
                if pd.notna(row["Ngày cập nhật"]) and pd.notna(row["NGÀY CẦN GIAO"]):
                    delta_days = (row["Ngày cập nhật"] - row["NGÀY CẦN GIAO"]).days
                    if delta_days > 0:
                        return f"trễ {delta_days} ngày"
                return "trễ" # Trạng thái trễ mặc định nếu không có dữ liệu ngày rõ ràng
            else:
                return "ok"

        # Áp dụng hàm tính toán trạng thái
        df_dashboard["TRẠNG THÁI"] = df_dashboard.apply(calculate_status, axis=1)
        
        # Sắp xếp và chỉ lọc ra các cột hiển thị chuẩn theo ảnh mẫu
        df_display = df_dashboard[["SỐ LÔ", "MÃ HÀNG", "TRẠNG THÁI"]].copy()
        df_display.sort_values(by=["SỐ LÔ", "MÃ HÀNG"], inplace=True)
        
        # Hàm định dạng màu sắc cho văn bản trực quan
        def style_status_rows(val):
            if "trễ" in str(val).lower():
                return "color: #D32F2F; font-weight: bold; background-color: #FFEBEE;"
            if "ok" in str(val).lower():
                return "color: #388E3C; font-weight: bold; background-color: #E8F5E9;"
            return ""

        # Giao diện bảng phụ hiển thị cấu trúc phân cấp (SỐ LÔ -> MÃ HÀNG -> TRẠNG THÁI)
        st.dataframe(
            df_display.style.applymap(style_status_rows, subset=["TRẠNG THÁI"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Vui lòng tải lên file đơn hàng để hệ thống tính toán trạng thái.")

# Toàn bộ logic vẽ đồ thị ma trận lịch sản xuất (df_matrix_schedule) của bạn sẽ tiếp tục chạy bình thường bên dưới...
