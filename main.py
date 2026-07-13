import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
from io import BytesIO

# =========================
# 1. CONFIG SYSTEM
# =========================
st.set_page_config(page_title="Production Schedule / 生产 plan", layout="wide")
st.title("📅 PRODUCTION SCHEDULE DASHBOARD / 生产排程看板")

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
}
h1 {
    font-size: 30px;
}
/* TABLE STYLE GLOBAL */
table {
    border-collapse: collapse !important;
    width: 100% !important;
}
td, th {
    text-align: center !important;
    vertical-align: middle !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE MANAGEMENT
# =========================
if "df_matrix_schedule" not in st.session_state:
    st.session_state.df_matrix_schedule = pd.DataFrame()
if "df_raw_schedule_history" not in st.session_state:
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
if "df_cumulative_orders" not in st.session_state:
    st.session_state.df_cumulative_orders = pd.DataFrame()

# SYSTEM RESET BUTTON
if st.sidebar.button("🗑️ Reset Toàn Bộ Hệ Thống / 重置系统"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.session_state.df_cumulative_orders = pd.DataFrame()
    st.sidebar.success("Đã xóa toàn bộ lịch sử và dữ liệu tích lũy! / 已清除所有历史与累计数据！")
    st.rerun()

# =========================
# 2. INPUT & DATA PROCESSING
# =========================
st.sidebar.header("⚙ CONFIG INPUT / 配置输入")
uploaded_file = st.sidebar.file_uploader("📂 Load đơn hàng mới / 加载新订单", type=["xlsx"])
inventory_file = st.sidebar.file_uploader("📦 Load file tồn kho hàng ngày / 加载每日库存", type=["xlsx"])

@st.cache_data(show_spinner=False)
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
        
        # Chuẩn hóa dữ liệu chuỗi
        df["SỐ MÁY"] = df["SỐ MÁY"].astype(str).str.strip()
        df["SỐ LÔ"] = df["SỐ LÔ"].astype(str).str.strip()
        df["MÃ HÀNG"] = df["MÃ HÀNG"].astype(str).str.strip()
        df = df.sort_values(["SỐ MÁY", "SỐ LÔ", "NGÀY ĐẶT HÀNG"], kind="stable")
        return df
    except Exception as e:
        st.sidebar.error(f"Lỗi cấu trúc file đơn hàng / 订单文件结构错误: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
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
        st.sidebar.error(f"Lỗi cấu trúc file tồn kho / 库存文件结构错误: {e}")
        return pd.DataFrame()

# BƯỚC 2.1: Tích hợp Đơn hàng mới
df_current_upload = load_orders(uploaded_file)
if not df_current_upload.empty:
    if st.session_state.df_cumulative_orders.empty:
        st.session_state.df_cumulative_orders = df_current_upload.copy()
    else:
        combined = pd.concat([st.session_state.df_cumulative_orders, df_current_upload], ignore_index=True)
        st.session_state.df_cumulative_orders = combined.drop_duplicates(
            subset=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"],
            keep="last"
        ).reset_index(drop=True)

# BƯỚC 2.2: Cập nhật Tồn kho động
df_inventory = load_inventory(inventory_file)
if not df_inventory.empty and not st.session_state.df_cumulative_orders.empty:
    temp_orders = pd.merge(st.session_state.df_cumulative_orders, df_inventory, on=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"], how="left")
    temp_orders["TỒN KHO"] = temp_orders["TỒN KHO MỚI"].fillna(temp_orders["TỒN KHO"])
    temp_orders.drop(columns=["TỒN KHO MỚI"], inplace=True)
    st.session_state.df_cumulative_orders = temp_orders.copy()
    st.sidebar.success("🔄 Cập nhật tồn kho mới thành công! / 新库存更新成功！")

df_orders = st.session_state.df_cumulative_orders.copy()

if df_orders.empty:
    st.warning("⚠️ Chưa có dữ liệu đơn hàng. Vui lòng tải lên tệp ở sidebar để bắt đầu. / 暂无订单数据。请在侧边栏上传文件以开始。")
    st.stop()

# =========================
# 3. GENERATION ENGINE (APPEND MODE & RE-CALCULATE LOGIC)
# =========================
if st.button("🚀 Generate / Refresh Schedule / 生成/刷新排程", type="primary"):
    start_planning_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    old_df = st.session_state.df_raw_schedule_history.copy()
    
    # Định dạng ngày lịch sử
    if not old_df.empty:
        old_df["Date_Obj"] = pd.to_datetime(old_df["Date_Obj"])
        old_df["SEQ"] = old_df["SEQ"].fillna(0).astype(int)

    # Nếu upload file tồn kho, tiến hành loại bỏ các lô cần tính toán lại
    if inventory_file is not None and not old_df.empty:
        for _, inv_row in df_inventory.iterrows():
            m_inv = inv_row["SỐ MÁY"]
            l_inv = inv_row["SỐ LÔ"]
            i_inv = inv_row["MÃ HÀNG"]
            old_df = old_df[~((old_df["SỐ MÁY"] == m_inv) & (old_df["SỐ LÔ"] == l_inv) & (old_df["MÃ HÀNG"] == i_inv))]

    # Khởi tạo bản đồ trạng thái thời gian thực của máy
    existing_keys = set()
    machine_last_date = {}
    machine_seq = {}
    
    if not old_df.empty:
        for _, r in old_df.iterrows():
            key = (str(r["SỐ MÁY"]), str(r["SỐ LÔ"]), str(r["MÃ HÀNG"]))
            existing_keys.add(key)
            m = str(r["SỐ MÁY"])
            machine_last_date[m] = max(machine_last_date.get(m, r["Date_Obj"]), r["Date_Obj"])
            machine_seq[m] = max(machine_seq.get(m, 0), int(r["SEQ"]))
            
        # Đẩy mốc tiến độ sang ngày kế tiếp đối với lịch cũ
        for m in machine_last_date:
            machine_last_date[m] = machine_last_date[m] + timedelta(days=1)
            
    new_records = []
    
    # Phân bổ điều độ tuần tự cho các đơn hàng chưa xếp
    for _, row in df_orders.iterrows():
        machine = str(row["SỐ MÁY"])
        lot = str(row["SỐ LÔ"])
        item = str(row["MÃ HÀNG"])
        
        if pd.isna(machine) or machine == "" or machine == "nan":
            continue
            
        key = (machine, lot, item)
        
        # Bỏ qua nếu đơn hàng đã được xếp lịch tĩnh trước đó và không đổi thông số kho
        if key in existing_keys and inventory_file is None:
            continue
            
        qty_needed = max(0, row["SL ĐẶT"] - row["TỒN KHO"])
        if qty_needed <= 0 or row["NĂNG SUẤT"] <= 0:
            continue
            
        if machine not in machine_last_date:
            machine_last_date[machine] = start_planning_date
        if machine not in machine_seq:
            machine_seq[machine] = 0
            
        # Sử dụng np.ceil làm tròn lên số ngày sản xuất an toàn
        days_needed = max(1, int(np.ceil(qty_needed / row["NĂNG SUẤT"])))
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

    # Hợp nhất lịch sử dữ liệu điều độ sản xuất
    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new["Date_Obj"] = pd.to_datetime(df_new["Date_Obj"])
        df_all = pd.concat([old_df, df_new], ignore_index=True)
    else:
        df_all = old_df
        
    df_all = df_all.sort_values(["SỐ MÁY", "SEQ"]).reset_index(drop=True)
    st.session_state.df_raw_schedule_history = df_all.copy()
    
    # Tái cấu trúc sang dạng Bảng Ma trận Phân bố dọc/ngang (Dịch tiêu đề hàng sang song ngữ)
    final_rows = []
    for machine_id, group in df_all.groupby("SỐ MÁY"):
        group = group.sort_values("SEQ")
        row_ngay = {"SỐ MÁY / 机号": machine_id, "Thuộc tính / 属性": "LỊCH / 日期"}
        row_lo = {"SỐ MÁY / 机号": machine_id, "Thuộc tính / 属性": "SỐ LÔ / 批号"}
        row_hang = {"SỐ MÁY / 机号": machine_id, "Thuộc tính / 属性": "MÃ HÀNG / 品号"}
        row_ns = {"SỐ MÁY / 机号": machine_id, "Thuộc tính / 属性": "NS / 产能"}
        
        for _, r in group.iterrows():
            col = f"C{int(r['SEQ'])}"
            row_ngay[col] = r["Date_Obj"].strftime("%d/%m")
            row_lo[col] = r["SỐ LÔ"]
            row_hang[col] = r["MÃ HÀNG"]
            row_ns[col] = int(r["NĂNG SUẤT"])
            
        final_rows.extend([row_ngay, row_lo, row_hang, row_ns])
        
    st.session_state.df_matrix_schedule = pd.DataFrame(final_rows)
    st.success("🎉 Đã đồng bộ và làm mới lịch sản xuất! / 生产排程已成功同步并刷新！")
    st.rerun()

# =========================
# 4. ADVANCED VISUAL MATRIX STYLING
# =========================
def style_matrix(df):
    if df.empty:
        return df
    lot_colors = {}
    
    # Lấy danh sách số lô duy nhất từ dữ liệu
    all_lots = df[df["Thuộc tính / 属性"].isin(["SỐ LÔ / 批号", "SỐ LÔ"])].drop(columns=["SỐ MÁY / 机号", "Thuộc tính / 属性"], errors="ignore").values.flatten()
    lots = list(dict.fromkeys([str(x) for x in all_lots if pd.notna(x) and str(x) != ""]))

    cmap = plt.get_cmap("tab20")
    for i, lot in enumerate(lots):
        lot_colors[lot] = mcolors.rgb2hex(cmap(i % 20))

    def color_cells(row):
        is_lot_row = row["Thuộc tính / 属性"] in ["SỐ LÔ / 批号", "SỐ LÔ"]
        styles = []
        for col_name, val in row.items():
            if col_name in ["SỐ MÁY / 机号", "Thuộc tính / 属性"]:
                styles.append("")
            elif is_lot_row and str(val) in lot_colors:
                styles.append(f"background-color: {lot_colors[str(val)]}; color: black; font-weight: bold;")
            else:
                styles.append("")
        return styles

    styled = df.style.apply(color_cells, axis=1)
    styled = styled.set_table_styles([
        {
            "selector": "th",
            "props": [
                ("background-color", "#1f4e79"),
                ("color", "white"),
                ("border", "1px solid #333"),
                ("text-align", "center"),
                ("font-weight", "bold")
            ]
        },
        {
            "selector": "td",
            "props": [
                ("border", "1px solid #ccc"),
                ("text-align", "center"),
                ("padding", "6px")
            ]
        }
    ])
    return styled

# =========================
# 5. RENDER DASHBOARD LAYOUT
# =========================
col_main, col_sub = st.columns([2, 1])

with col_main:
    if not st.session_state.df_matrix_schedule.empty:
        st.subheader("🗓️ CHÍNH: MA TRẬN LỊCH SẢN XUẤT TRÊN MÁY / 主表：机台生产排程矩阵")
        st.dataframe(
            style_matrix(st.session_state.df_matrix_schedule),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("💡 Chưa có dữ liệu ma trận lịch trình. Vui lòng nhấn nút 'Generate / Refresh Schedule' phía trên để chạy tính toán phân bổ máy. / 暂无排程矩阵数据。")

with col_sub:
    st.subheader("📊 PHỤ: TIẾN ĐỘ THỜI GIAN THỰC / 副表：实时进度与状态")
    if not df_orders.empty:
        # Lấy ngày kết thúc thực tế từ lịch sử (nếu có)
        df_history = st.session_state.df_raw_schedule_history.copy()
        if not df_history.empty:
            df_end_date = df_history.groupby(["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"], as_index=False)["Date_Obj"].max()
            df_end_date.rename(columns={"Date_Obj": "NGÀY HOÀN THÀNH THỰC TẾ"}, inplace=True)
            df_status = pd.merge(
                df_orders[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "SL ĐẶT", "TỒN KHO"]],
                df_end_date,
                on=["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"],
                how="left"
            )
        else:
            df_status = df_orders[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "SL ĐẶT", "TỒN KHO"]].copy()
            df_status["NGÀY HOÀN THÀNH THỰC TẾ"] = np.nan

        def check_status(row):
            # 1. Kiểm tra nếu đơn hàng chưa được xếp lịch sản xuất
            if pd.isna(row["NGÀY HOÀN THÀNH THỰC TẾ"]):
                if (row["SL ĐẶT"] - row["TỒN KHO"]) <= 0:
                    return "🟢 Đủ Tồn Kho (OK) / 库存充足"
                return "⚪ Chưa sắp lịch / 未排程"

            # 2. Ép kiểu dữ liệu an toàn về dạng Timestamp của Pandas
            ts_real = pd.to_datetime(row["NGÀY HOÀN THÀNH THỰC TẾ"])
            ts_delivery = pd.to_datetime(row["NGÀY GIAO"])

            if pd.isna(ts_delivery):
                return "🟢 Kế hoạch Đạt (OK) / 正常达成"

            # 3. Tiến hành trích xuất .date() để so sánh logic giữa các ngày
            date_real = ts_real.date()
            date_delivery = ts_delivery.date()

            if date_real > date_delivery:
                delay_days = (date_real - date_delivery).days
                return f"🔴 Trễ {delay_days} ngày / 延期 {delay_days} 天"
            else:
                return "🟢 Kế hoạch Đạt (OK) / 正常达成"

        df_status["TRẠNG THÁI / 状态"] = df_status.apply(check_status, axis=1)
        
        # Đổi tên cột hiển thị bảng phụ sang song ngữ
        df_display_status = df_status[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "TRẠNG THÁI / 状态"]].copy()
        df_display_status.columns = ["SỐ MÁY / 机号", "SỐ LÔ / 批号", "MÃ HÀNG / 品号", "TRẠNG THÁI / 状态"]

        def style_status_rows(val):
            if "🔴" in str(val):
                return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
            elif "🟢" in str(val):
                return "background-color: #e2f0d9; color: #385723;"
            return ""

        styled_sub_table = (
            df_display_status.style
            .apply(lambda x: [style_status_rows(v) for v in x], subset=["TRẠNG THÁI / 状态"])
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [("background-color", "#2f5597"), ("color", "white"), ("font-weight", "bold")]
                },
                {
                    "selector": "td",
                    "props": [("border", "1px solid #ccc"), ("padding", "5px")]
                }
            ])
        )

        st.dataframe(styled_sub_table, use_container_width=True, hide_index=True)
    else:
        st.info("Hệ thống chưa có đủ lịch trình để cấu trúc bảng kiểm soát trạng thái.")

