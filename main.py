import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
from io import BytesIO

# =========================
# 1. CONFIG & CSS FOR PROFESSIONAL TABLE
# =========================
st.set_page_config(page_title="Production Schedule / 生产 kế hoạch", layout="wide")
st.title("📅 PRODUCTION SCHEDULE DASHBOARD / 生产排程看板")

# CSS Ép toàn bộ thành phần bảng hiển thị của Streamlit phải căn giữa và kẻ viền rõ ràng
st.markdown("""
<style>
.block-container { padding-top: 1rem; }
h1 { font-size: 30px; }

/* Ép kiểu trên toàn bộ giao diện bảng HTML */
div[data-testid="stDataFrame"] table, 
div[data-testid="stDataFrame"] .stTable, 
table {
    border-collapse: collapse !important;
    width: 100% !important;
    border: 1px solid #333333 !important;
}

div[data-testid="stDataFrame"] th, th {
    background-color: #1f4e79 !important;
    color: white !important;
    text-align: center !important;
    vertical-align: middle !important;
    font-weight: bold !important;
    border: 1px solid #333333 !important;
    padding: 8px !important;
}

div[data-testid="stDataFrame"] td, td, [data-testid="styled-table-cell"] {
    text-align: center !important;
    vertical-align: middle !important;
    border: 1px solid #888888 !important;
    padding: 8px !important;
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

# RESET
if st.sidebar.button("🗑️ Reset Schedule History / 清空排程歷史"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.sidebar.success("Schedule history cleared! / 排程歷史已清空！")
    st.rerun()

# =========================
# INPUT
# =========================
st.sidebar.header("⚙ INPUT / 輸入")
uploaded_file = st.sidebar.file_uploader("📂 Upload Order File / 上傳訂單文件", type=["xlsx"])

def load_orders(file):
    if file is None:
        return pd.DataFrame()

    df = pd.read_excel(file, sheet_name="DonHang")

    df["NGÀY GIAO"] = pd.to_datetime(df["NGÀY GIAO"], errors="coerce")
    df["NGÀY ĐẶT HÀNG"] = pd.to_datetime(df["NGÀY ĐẶT HÀNG"], errors="coerce")
    df["NĂNG SUẤT"] = pd.to_numeric(df["NĂNG SUẤT"], errors="coerce").fillna(0)
    df["SL ĐẶT"] = pd.to_numeric(df["SL ĐẶT"], errors="coerce").fillna(0)
    df["TỒN KHO"] = pd.to_numeric(df["TỒN KHO"], errors="coerce").fillna(0)

    df = df.sort_values(["SỐ MÁY", "SỐ LÔ", "NGÀY ĐẶT HÀNG"], kind="stable")
    return df

df_orders = load_orders(uploaded_file)

if df_orders.empty:
    st.warning("No order data available. / 暫無訂單數據。")
    st.stop()

# =========================
# GENERATE (LOGIC UNCHANGED)
# =========================
if st.button("🚀 Generate / Refresh Schedule | 生成/刷新排程"):

    start_planning_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    old_df = st.session_state.df_raw_schedule_history.copy()

    existing_keys = set()
    machine_last_date = {}
    machine_seq = {}

    if not old_df.empty:
        old_df["Date_Obj"] = pd.to_datetime(old_df["Date_Obj"])
        old_df["SEQ"] = old_df["SEQ"].fillna(0).astype(int)

        for _, r in old_df.iterrows():
            key = (r["SỐ MÁY"], r["SỐ LÔ"], r["MÃ HÀNG"])
            existing_keys.add(key)

            m = r["SỐ MÁY"]
            machine_last_date[m] = max(machine_last_date.get(m, r["Date_Obj"]), r["Date_Obj"])
            machine_seq[m] = max(machine_seq.get(m, 0), int(r["SEQ"]))

        for m in machine_last_date:
            machine_last_date[m] = machine_last_date[m] + timedelta(days=1)

    new_records = []

    for _, row in df_orders.iterrows():

        machine = row["SỐ MÁY"]
        lot = row["SỐ LÔ"]
        item = row["MÃ HÀNG"]

        if pd.isna(machine) or machine == "":
            continue

        key = (machine, lot, item)

        if key in existing_keys:
            continue

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

    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new["Date_Obj"] = pd.to_datetime(df_new["Date_Obj"])
        df_all = pd.concat([old_df, df_new], ignore_index=True)
    else:
        df_all = old_df

    df_all = df_all.sort_values(["SỐ MÁY", "SEQ"]).reset_index(drop=True)
    st.session_state.df_raw_schedule_history = df_all.copy()

    final_rows = []

    for machine_id, group in df_all.groupby("SỐ MÁY"):

        group = group.sort_values("SEQ")

        # Gộp dòng số máy: Chỉ hiển thị tên máy ở dòng SCHEDULE, các dòng sau để rỗng ""
        row_ngay = {"SỐ MÁY / 机台": machine_id, "THUỘC TÍNH / 属性": "SCHEDULE / 排程日期"}
        row_lo = {"SỐ MÁY / 机台": "", "THUỘC TÍNH / 属性": "LOT / 批号"}
        row_hang = {"SỐ MÁY / 机台": "", "THUỘC TÍNH / 属性": "ITEM / 品号"}
        row_ns = {"SỐ MÁY / 机台": "", "THUỘC TÍNH / 属性": "OUTPUT / 产能"}

        # Cột ẩn kỹ thuật để phục vụ việc tô màu
        row_ngay["_ORIGINAL_MACHINE"] = machine_id
        row_lo["_ORIGINAL_MACHINE"] = machine_id
        row_hang["_ORIGINAL_MACHINE"] = machine_id
        row_ns["_ORIGINAL_MACHINE"] = machine_id

        for _, r in group.iterrows():
            col = f"C{int(r['SEQ'])}"
            row_ngay[col] = r["Date_Obj"].strftime("%d/%m")
            row_lo[col] = r["SỐ LÔ"]
            row_hang[col] = r["MÃ HÀNG"]
            row_ns[col] = int(r["NĂNG SUẤT"])

        final_rows.extend([row_ngay, row_lo, row_hang, row_ns])

    st.session_state.df_matrix_schedule = pd.DataFrame(final_rows)
    st.success("Schedule updated successfully / 排程更新成功！")

# =========================
# STYLE (MACHINE + LOT COLOR FIXED)
# =========================
def style_matrix(df):

    cmap = plt.get_cmap("tab20")

    color_map = {}
    color_index = 0

    for machine in df["_ORIGINAL_MACHINE"].unique():

        lot_row = df[(df["_ORIGINAL_MACHINE"] == machine) & (df["THUỘC TÍNH / 属性"] == "LOT / 批号")]

        if lot_row.empty:
            continue

        for col in lot_row.columns:
            if col in ["SỐ MÁY / 机台", "THUỘC TÍNH / 属性", "_ORIGINAL_MACHINE"]:
                continue

            lot = str(lot_row[col].values[0])

            key = (machine, lot)

            if lot not in ["nan", "None", ""]:
                if key not in color_map:
                    color_map[key] = mcolors.rgb2hex(cmap(color_index % 20))
                    color_index += 1

    def get_color(machine, lot):
        return color_map.get((machine, str(lot)), "")

    def apply_color(row):
        machine = row["_ORIGINAL_MACHINE"]
        colors = []

        for col in row.index:

            if col in ["SỐ MÁY / 机台", "THUỘC TÍNH / 属性", "_ORIGINAL_MACHINE"]:
                colors.append("")
                continue

            lot_val = df.loc[
                (df["_ORIGINAL_MACHINE"] == machine) &
                (df["THUỘC TÍNH / 属性"] == "LOT / 批号"),
                col
            ].values

            lot_val = str(lot_val[0]) if len(lot_val) > 0 else ""

            colors.append(f"background-color: {get_color(machine, lot_val)}")

        return colors

    styled = df.style.apply(apply_color, axis=1)

    # Ẩn cột kỹ thuật "_ORIGINAL_MACHINE"
    if "_ORIGINAL_MACHINE" in df.columns:
        styled = styled.hide(["_ORIGINAL_MACHINE"], axis="columns")

    # Ép cấu trúc CSS Nội bộ vào thẳng đối tượng Styler (Fix triệt để lỗi mất khung/lệch hàng của Streamlit)
    styled = styled.set_table_styles([
        {"selector": "th", "props": [
            ("background-color", "#1f4e79"),
            ("color", "white"),
            ("border", "1px solid #333333 !important"),
            ("text-align", "center !important"),
            ("vertical-align", "middle !important"),
            ("font-weight", "bold"),
            ("padding", "8px")
        ]},
        {"selector": "td", "props": [
            ("border", "1px solid #888888 !important"),
            ("text-align", "center !important"),
            ("vertical-align", "middle !important"),
            ("padding", "8px")
        ]},
        {"selector": "", "props": [
            ("border-collapse", "collapse !important"),
            ("width", "100% !important")
        ]}
    ], overwrite=False)

    return styled

# =========================
# 2 & 3. UPLOAD INVENTORY & DELAY ALERTS
# =========================
st.markdown("---")
st.subheader("📦 INVENTORY UPDATE & DELAY ALERT SYSTEM / 库存更新与交期延迟预警系统")

# Nút Upload file tồn kho
inv_file = st.file_uploader("📂 Upload Inventory File / 上傳庫存文件 (Cập nhật Tồn Kho / 更新庫存量)", type=["xlsx"], key="inv_upload")

df_orders_calc = df_orders.copy()

if inv_file is None:
    st.info("💡 Chưa upload file tồn kho mới. Hệ thống đang tính toán cảnh báo dựa trên số lượng tồn kho ban đầu. / 尚未上傳新庫存文件。系統正基於初始庫存量計算預警。")
else:
    try:
        df_inv = pd.read_excel(inv_file)
        df_inv.columns = [str(c).strip().upper() for c in df_inv.columns]
        
        ma_hang_col = None
        for c in df_inv.columns:
            if "MÃ HÀNG" in c or "品号" in c or "ITEM" in c:
                ma_hang_col = c
                break
        if ma_hang_col is None and len(df_inv.columns) > 0:
            ma_hang_col = df_inv.columns[0]
            
        if ma_hang_col:
            qty_col = None
            for c in df_inv.columns:
                if "TỒN KHO" in c or "库存" in c or "SL TỒN" in c or "QTY" in c:
                    qty_col = c
                    break
            if qty_col is None and len(df_inv.columns) > 1:
                qty_col = df_inv.columns[1]
                
            if qty_col:
                df_inv[qty_col] = pd.to_numeric(df_inv[qty_col], errors="coerce").fillna(0)
                inv_dict = df_inv.groupby(ma_hang_col)[qty_col].sum().to_dict()
                
                df_orders_calc["TỒN KHO"] = df_orders_calc.apply(
                    lambda r: r["TỒN KHO"] + inv_dict.get(r["MÃ HÀNG"], 0), axis=1
                )
                st.success("⚡ Đã cộng dồn dữ liệu tồn kho mới vào hệ thống tính toán cảnh báo! / 新庫存數據已成功累加至預警系統！")
            else:
                st.error("File tồn kho cần có cột chứa số lượng hàng tồn. / 庫存文件需包含數量列。")
        else:
            st.error("File tồn kho không tìm thấy cột mã hàng. / 庫存文件未找到品號列。")
    except Exception as e:
        st.error(f"Lỗi đọc file tồn kho / 讀取庫存文件出錯: {e}")

df_history = st.session_state.df_raw_schedule_history.copy()

if not df_history.empty and not df_orders_calc.empty:
    df_history["Date_Obj"] = pd.to_datetime(df_history["Date_Obj"])
    
    df_delivery_actual = df_history.groupby(["SỐ LÔ", "MÃ HÀNG"])["Date_Obj"].max().reset_index()
    df_delivery_actual.rename(columns={"Date_Obj": "NGÀY_GIAO_THỰC_TẾ"}, inplace=True)
    
    df_alert_merge = pd.merge(df_orders_calc, df_delivery_actual, on=["SỐ LÔ", "MÃ HÀNG"], how="inner")
    
    alert_records = []
    for _, row in df_alert_merge.iterrows():
        ngay_giao_khach = row["NGÀY GIAO"]
        ngay_giao_thucte = row["NGÀY_GIAO_THỰC_TẾ"]
        
        if pd.notna(ngay_giao_khach) and pd.notna(ngay_giao_thucte):
            so_ngay_tre = (ngay_giao_thucte - ngay_giao_khach).days
            
            if so_ngay_tre > 0:
                total_qty_needed = max(0, row["SL ĐẶT"] - row["TỒN KHO"])
                sl_thieu = min(total_qty_needed, so_ngay_tre * row["NĂNG SUẤT"])
                
                if sl_thieu > 0:
                    alert_records.append({
                        "SỐ LÔ / 批号": row["SỐ LÔ"],
                        "MÃ HÀNG / 品号": row["MÃ HÀNG"],
                        "NGÀY GIAO / 交期": ngay_giao_khach.strftime("%d/%m/%Y"),
                        "SỐ NGÀY TRỂ / 延误天数": so_ngay_tre,
                        "SỐ LƯỢNG THIẾU / 欠数": int(sl_thieu)
                    })
                    
    if alert_records:
        df_alert_display = pd.DataFrame(alert_records)
        st.error("⚠️ BẢNG CẢNH BÁO TRẠNG THÁI VỀ TRỄ HÀNG / 交期交货延误状态交期预警表")
        
        # Bảng cảnh báo được tiêm trực tiếp style căn giữa và kẻ viền vào lõi Styler
        styled_alert = df_alert_display.style.set_table_styles([
            {"selector": "th", "props": [
                ("background-color", "#d9534f"), 
                ("color", "white"), 
                ("font-weight", "bold"), 
                ("border", "1px solid #333333 !important"),
                ("text-align", "center !important"),
                ("vertical-align", "middle !important"),
                ("padding", "8px")
            ]},
            {"selector": "td", "props": [
                ("border", "1px solid #888888 !important"), 
                ("text-align", "center !important"),
                ("vertical-align", "middle !important"),
                ("padding", "8px")
            ]}
        ], overwrite=False)
        st.dataframe(styled_alert, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Hiện tại không có lô hàng nào bị trễ (Dashboard gọn gàng!) / 目前無任何批次延誤（看板整洁！）")
else:
    st.info("Chưa có dữ liệu lịch xếp hoặc đơn hàng để thực hiện tính toán bảng cảnh báo. / 暫無排程歷史數據或訂單數據以供計算預警。")

# =========================
# DISPLAY SCHEDULE
# =========================
st.markdown("---")
if not st.session_state.df_matrix_schedule.empty:

    st.subheader("📅 Production Schedule / 生产排程表")

    # Hiển thị bảng lịch sản xuất đã găm sẵn Style ép viền và căn giữa
    st.dataframe(
        style_matrix(st.session_state.df_matrix_schedule),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📥 Export Excel / 匯出 Excel")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        columns_to_export = [c for c in st.session_state.df_matrix_schedule.columns if c != "_ORIGINAL_MACHINE"]
        st.session_state.df_matrix_schedule[columns_to_export].to_excel(writer, index=False, sheet_name="Schedule")

    st.download_button(
        "💾 Download Excel / 下載 Excel",
        data=output.getvalue(),
        file_name=f"Production_Schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
