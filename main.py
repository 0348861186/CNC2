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

# Lưu trữ lũy kế đơn hàng tổng hợp qua nhiều lần load file
if "df_cumulative_orders" not in st.session_state:
    st.session_state.df_cumulative_orders = pd.DataFrame()

# RESET
if st.sidebar.button("🗑️ Reset Toàn Bộ Hệ Thống"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.session_state.df_cumulative_orders = pd.DataFrame()
    st.sidebar.success("Đã xóa lịch sử lịch trình và đơn hàng tổng hợp!")
    st.rerun()

# =========================
# 2. INPUT & DATA PROCESSING
# =========================
st.sidebar.header("⚙ INPUT")
uploaded_file = st.sidebar.file_uploader("📂 Load đơn hàng", type=["xlsx"])
inventory_file = st.sidebar.file_uploader("📦 Load file tồn kho hàng ngày", type=["xlsx"])

# Hàm xử lý file đơn hàng
def load_orders(file):
    if file is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(file, sheet_name="DonHang")
        df["NGÀY GIAO"] = pd.to_datetime(df["NGÀY GIAO"], errors="coerce")
        df["NGÀY ĐẶT HÀNG"] = pd.to_datetime(df["NGÀY ĐẶT HÀNG"], errors="coerce")
        df["NĂNG SUẤT"] = pd.to_numeric(df["NĂNG SUẤT"], errors="coerce").fillna(0)
        df["SL ĐẶT"] = pd.to_numeric(df["SL ĐẶT"], errors="coerce").fillna(0)
        df["TỒN KHO"] = pd.to_numeric(df["TỒN KHO"], errors="coerce").fillna(0)
        
        # Làm sạch chuỗi khóa
        df["SỐ MÁY"] = df["SỐ MÁY"].astype(str).str.strip()
        df["SỐ LÔ"] = df["SỐ LÔ"].astype(str).str.strip()
        df["MÃ HÀNG"] = df["MÃ HÀNG"].astype(str).str.strip()
        
        df = df.sort_values(["SỐ MÁY", "SỐ LÔ", "NGÀY ĐẶT HÀNG"], kind="stable")
        return df
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file đơn hàng: {e}")
        return pd.DataFrame()

# Hàm xử lý file tồn kho
def load_inventory(file):
    if file is None:
        return pd.DataFrame()
    try:
        df_inv = pd.read_excel(file)
        df_inv["SỐ MÁY"] = df_inv["SỐ MÁY"].astype(str).str.strip()
        df_inv["SỐ LÔ"] = df_inv["SỐ LÔ"].astype(str).str.strip()
        df_inv["MÃ HÀNG"] = df_inv["MÃ HÀNG"].astype(str).str.strip()
        df_inv["TỒN KHO MỚI"] = pd.to_numeric(df_inv["TỒN KHO"], errors="coerce").fillna(0)
        return df_inv[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "TỒN KHO MỚI"]]
    except Exception as e:
        st.sidebar.error(f"Lỗi đọc file tồn kho: {e}")
        return pd.DataFrame()

# BƯỚC 2.1: Xử lý Đơn hàng mới và gộp lũy kế
df_current_upload = load_orders(uploaded_file)

if not df_current_upload.empty:
    if st.session_state.df_cumulative_orders.empty:
        st.session_state.df_cumulative_orders = df_current_upload.copy()
    else:
        combined = pd.concat([st.session_state.df_cumulative_orders, df_current_upload], ignore_index=True)
        st.session_state.df_cumulative_orders = combined.drop_duplicates(
            subset=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"], keep="last"
        ).reset_index(drop=True)

# BƯỚC 2.2: Cập nhật Tồn kho hàng ngày nếu có file load lên
df_inventory = load_inventory(inventory_file)
if not df_inventory.empty and not st.session_state.df_cumulative_orders.empty:
    temp_orders = pd.merge(st.session_state.df_cumulative_orders, df_inventory, on=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"], how="left")
    temp_orders["TỒN KHO"] = temp_orders["TỒN KHO MỚI"].fillna(temp_orders["TỒN KHO"])
    temp_orders.drop(columns=["TỒN KHO MỚI"], inplace=True)
    st.session_state.df_cumulative_orders = temp_orders.copy()
    st.sidebar.success("🔄 Đã cập nhật Tồn kho mới vào bộ nhớ hệ thống!")

# Gán biến làm việc chính là danh sách đơn hàng đã tích lũy tổng hợp
df_orders = st.session_state.df_cumulative_orders.copy()

if df_orders.empty:
    st.warning("⚠️ Chưa có dữ liệu đơn hàng. Vui lòng load file đơn hàng ở sidebar để bắt đầu.")
    st.stop()

# =========================
# 3. GENERATE (APPEND-ONLY FIXED WITH CURRENT LOGIC)
# =========================
if st.button("🚀 Generate / Refresh Schedule"):

    start_planning_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    old_df = st.session_state.df_raw_schedule_history.copy()

    # =========================
    # KEY FIX 1: lấy lịch cũ
    # =========================
    existing_keys = set()
    machine_last_date = {}
    machine_seq = {}

    if not old_df.empty:
        old_df["Date_Obj"] = pd.to_datetime(old_df["Date_Obj"])
        old_df["SEQ"] = old_df["SEQ"].fillna(0).astype(int)

        for _, r in old_df.iterrows():
            key = (str(r["SỐ MÁY"]), str(r["SỐ LÔ"]), str(r["MÃ HÀNG"]))
            existing_keys.add(key)

            m = str(r["SỐ MÁY"])
            machine_last_date[m] = max(machine_last_date.get(m, r["Date_Obj"]), r["Date_Obj"])
            machine_seq[m] = max(machine_seq.get(m, 0), int(r["SEQ"]))

        # tiếp nối ngày (KHÔNG gap)
        for m in machine_last_date:
            machine_last_date[m] = machine_last_date[m] + timedelta(days=1)

    new_records = []

    # =========================
    # KEY FIX 2: CHỈ ADD ORDER MỚI HOẶC ORDER ĐÃ ĐƯỢC THAY ĐỔI TỒN KHO TÍNH TOÁN LẠI
    # =========================
    for _, row in df_orders.iterrows():

        machine = str(row["SỐ MÁY"])
        lot = str(row["SỐ LÔ"])
        item = str(row["MÃ HÀNG"])

        if pd.isna(machine) or machine == "" or machine == "nan":
            continue

        key = (machine, lot, item)

        # Nếu đơn hàng đã chạy rồi và không có file cập nhật mới thay đổi, giữ nguyên tránh overwrite lịch cũ
        if key in existing_keys and inventory_file is None:
            continue
            
        # Nếu có file tồn kho mới, xóa lịch cũ của đúng Lô đó trong old_df để tính toán lại ngày phân bổ mới
        if key in existing_keys and inventory_file is not None:
            old_df = old_df[~((old_df["SỐ MÁY"] == machine) & (old_df["SỐ LÔ"] == lot) & (old_df["MÃ HÀNG"] == item))]

        qty_needed = max(0, row["SL ĐẶT"] - row["TỒN KHO"])
        if qty_needed <= 0 or row["NĂNG SUẤT"] <= 0:
            continue

        if machine not in machine_last_date:
            machine_last_date[machine] = start_planning_date

        if machine not in machine_seq:
            machine_seq[machine] = 0

        days_needed = max(1, int(round(qty_needed / row["NĂNG SUẤT"])))

        start_day = machine_last_date[machine]
        start_seq = machine_seq[machine]

        for d in range(days_needed):
            new_records.append({
                "SỐ MÁY": machine,
                "Date_Obj": start_day + timedelta(days=d),
                "SEQ": start_seq + d + 1,
                "SỐ LÔ": lot,
                "MÃ HÀNG": item,
                "NĂNG SUẤT": int(row["NĂNG SUẤT"])
            })

        machine_last_date[machine] = start_day + timedelta(days=days_needed)
        machine_seq[machine] = start_seq + days_needed

    # =========================
    # MERGE OLD + NEW (NO OVERWRITE)
    # =========================
    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new["Date_Obj"] = pd.to_datetime(df_new["Date_Obj"])

        if not old_df.empty:
            df_combined = pd.concat([old_df, df_new], ignore_index=True)
        else:
            df_combined = df_new
    else:
        df_combined = old_df

    if not df_combined.empty:
        df_combined = df_combined.sort_values(["SỐ MÁY", "SEQ"], kind="stable").reset_index(drop=True)
        
    st.session_state.df_raw_schedule_history = df_combined
    st.success("🚀 Đã xử lý lịch trình hoàn tất!")

# =========================
# 4. DISPLAY MA TRẬN LỊCH TRÌNH
# =========================
df_history = st.session_state.df_raw_schedule_history.copy()

if not df_history.empty:
    st.subheader("📋 Bảng Lịch Trình Chi Tiết (Dạng Ma Trận)")
    
    # Định dạng ngày ngắn gọn để hiển thị header cột (VD: 2024-03-20)
    df_history["Ngày"] = df_history["Date_Obj"].dt.strftime('%Y-%m-%d')
    df_history["Thông tin Lô"] = df_history["SỐ LÔ"] + " (" + df_history["MÃ HÀNG"] + ")"
    
    # Tạo Pivot table thành dạng ma trận: Dòng = SỐ MÁY, Cột = Ngày, Giá trị = Số Lô (Mã Hàng)
    try:
        df_pivot = df_history.pivot(index="SỐ MÁY", columns="Ngày", values="Thông tin Lô").fillna("-")
        st.dataframe(df_pivot, use_container_width=True)
        
        # Hiển thị thêm bảng data thô nếu cần đối soát
        with st.expander("🔍 Xem dữ liệu thô dạng bảng (Raw Data)"):
            st.dataframe(df_history[["SỐ MÁY", "Ngày", "SEQ", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT"]], use_container_width=True)
    except Exception as e:
        st.error(f"Lỗi tạo bảng ma trận hiển thị: {e}")
