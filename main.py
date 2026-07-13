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
st.title("📅 PRODUCTION SCHEDULE DASHBOARD / 生产排程看板")

st.markdown("""
<style>
.block-container { padding-top: 1rem; }
h1 { font-size: 30px; }

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

# RESET
if st.sidebar.button("🗑️ Reset Schedule History / 重置排程历史"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.sidebar.success("Schedule history cleared! / 排程历史已清除！")
    st.rerun()

# =========================
# INPUT
# =========================
st.sidebar.header("⚙ INPUT / 输入")
uploaded_file = st.sidebar.file_uploader("📂 Upload Order File / 上传订单文件", type=["xlsx"])

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
    st.warning("No order data available. / 暂无订单数据。")
    st.stop()

# =========================
# GENERATE (LOGIC UNCHANGED)
# =========================
if st.button("🚀 Generate / Refresh Schedule | 生成 / 刷新排程"):

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

        # LOGIC GỐC GIỮ NGUYÊN 100%: Sử dụng đúng từ khoá gốc hệ thống
        row_ngay = {"SỐ MÁY": machine_id, "Attribute": "SCHEDULE"}
        row_lo = {"SỐ MÁY": machine_id, "Attribute": "LOT"}
        row_hang = {"SỐ MÁY": machine_id, "Attribute": "ITEM"}
        row_ns = {"SỐ MÁY": machine_id, "Attribute": "OUTPUT"}

        for _, r in group.iterrows():
            col = f"C{int(r['SEQ'])}"
            row_ngay[col] = r["Date_Obj"].strftime("%d/%m")
            row_lo[col] = r["SỐ LÔ"]
            row_hang[col] = r["MÃ HÀNG"]
            row_ns[col] = int(r["NĂNG SUẤT"])

        final_rows.extend([row_ngay, row_lo, row_hang, row_ns])

    st.session_state.df_matrix_schedule = pd.DataFrame(final_rows)
    st.success("Schedule updated successfully / 排程更新成功")

# =========================
# STYLE (MACHINE + LOT COLOR FIXED)
# =========================
def style_matrix(df):
    # Tạo bản sao cục bộ để xử lý giao diện hiển thị
    display_df = df.copy()

    cmap = plt.get_cmap("tab20")
    color_map = {}
    color_index = 0

    # Bước 1: Tính toán bảng màu dựa trên cấu trúc dữ liệu gốc của bảng truyền vào
    for machine in display_df["SỐ MÁY"].unique():
        lot_row = display_df[(display_df["SỐ MÁY"] == machine) & (display_df["Attribute"] == "LOT")]

        if lot_row.empty:
            continue

        for col in lot_row.columns:
            if col in ["SỐ MÁY", "Attribute"]:
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
        # Lúc này row đã mang các tiêu đề cột song ngữ do chúng ta gán ở Bước 3 dưới đây
        machine = row["SỐ MÁY / 机台号"]
        colors = []

        for col in row.index:
            if col in ["SỐ MÁY / 机台号", "THUỘC TÍNH / 属性"]:
                colors.append("")
                continue

            # Tìm kiếm dòng LOT dựa trên tên cột mới đã đổi sang tiếng Trung
            lot_val = display_df.loc[
                (display_df["SỐ MÁY / 机台号"] == machine) &
                (display_df["THUỘC TÍNH / 属性"] == "LOT / 批号"),
                col
            ].values

            lot_val = str(lot_val[0]) if len(lot_val) > 0 else ""
            colors.append(f"background-color: {get_color(machine, lot_val)}")

        return colors

    # Bước 2: Song ngữ hóa dữ liệu dòng của cột Attribute trước
    attr_translation = {
        "SCHEDULE": "SCHEDULE / 排程日期",
        "LOT": "LOT / 批号",
        "ITEM": "ITEM / 品号",
        "OUTPUT": "OUTPUT / 产能"
    }
    display_df["Attribute"] = display_df["Attribute"].map(attr_translation).fillna(display_df["Attribute"])

    # Bước 3: Đổi tên tiêu đề cột trực tiếp trên DataFrame bằng thuộc tính .columns (Tương thích 100% mọi phiên bản Pandas)
    new_columns = ["SỐ MÁY / 机台号", "THUỘC TÍNH / 属性"] + list(display_df.columns[2:])
    display_df.columns = new_columns

    # Bước 4: Áp dụng style màu sắc lên DataFrame đã chuyển đổi hoàn chỉnh sang song ngữ
    styled = display_df.style.apply(apply_color, axis=1)

    styled = styled.set_table_styles([
        {"selector": "th",
         "props": [
             ("background-color", "#1f4e79"),
             ("color", "white"),
             ("border", "1px solid #333"),
             ("text-align", "center"),
             ("font-weight", "bold")
         ]},
        {"selector": "td",
         "props": [
             ("border", "1px solid #ccc"),
             ("text-align", "center"),
             ("padding", "6px")
         ]},
        {"selector": "table",
         "props": [
             ("border-collapse", "collapse"),
             ("width", "100%")
         ]}
    ])

    return styled

# =========================
# 2 & 3. UPLOAD INVENTORY & DELAY ALERTS
# =========================
st.markdown("---")
st.subheader("📦 INVENTORY UPDATE & DELAY ALERT SYSTEM / 库存更新与延期预警系统")

# Nút upload file tồn kho trên dashboard
inv_file = st.file_uploader("📂 Upload Inventory File (Cập nhật Tồn Kho) / 上传库存文件 (更新库存)", type=["xlsx"], key="inv_upload")

# Bản sao dữ liệu order để tính toán cảnh báo mà không ảnh hưởng tới lịch đã xếp
df_orders_calc = df_orders.copy()

if inv_file is None:
    st.info("💡 Chưa upload file tồn kho mới. Hệ thống đang tính toán cảnh báo dựa trên số lượng tồn kho ban đầu. / 未上传新库存文件。系统将基于初始库存量计算预警。")
else:
    try:
        df_inv = pd.read_excel(inv_file)
        
        df_inv.columns = [str(c).strip().upper() for c in df_inv.columns]
        if "MÃ HÀNG" in df_inv.columns:
            qty_col = "TỒN KHO" if "TỒN KHO" in df_inv.columns else (df_inv.columns[1] if len(df_inv.columns) > 1 else None)
            
            if qty_col:
                df_inv[qty_col] = pd.to_numeric(df_inv[qty_col], errors="coerce").fillna(0)
                inv_dict = df_inv.groupby("MÃ HÀNG")[qty_col].sum().to_dict()
                
                df_orders_calc["TỒN KHO"] = df_orders_calc.apply(
                    lambda r: r["TỒN KHO"] + inv_dict.get(r["MÃ HÀNG"], 0), axis=1
                )
                st.success("⚡ Đã cộng dồn dữ liệu tồn kho mới vào hệ thống tính toán cảnh báo! / 新库存数据已成功累加至预警系统！")
            else:
                st.error("File tồn kho cần có cột chứa số lượng hàng tồn. / 库存文件需包含库存数量列。")
        else:
            st.error("File tồn kho không tìm thấy cột 'MÃ HÀNG'. / 库存文件中未找到“MÃ HÀNG”列。")
    except Exception as e:
        st.error(f"Lỗi đọc file tồn kho / 读取库存文件出错: {e}")

# Tiến hành tính toán bảng cảnh báo trạng thái trễ hàng dựa trên df_raw_schedule_history hiện tại
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
                        "SỐ NGÀY TRỄ / 延期天数": so_ngay_tre,
                        "SỐ LƯỢNG THIẾU / 欠数": int(sl_thieu)
                    })
                    
    if alert_records:
        df_alert_display = pd.DataFrame(alert_records)
        st.error("⚠️ BẢNG CẢNH BÁO TRẠNG THÁI VỀ TRỄ HÀNG / 订单交期延期预警表")
        
        styled_alert = df_alert_display.style.set_table_styles([
            {"selector": "th", "props": [("background-color", "#d9534f"), ("color", "white"), ("font-weight", "bold")]},
            {"selector": "td", "props": [("border", "1px solid #ccc"), ("padding", "8px")]}
        ])
        st.dataframe(styled_alert, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Hiện tại không có lô hàng nào bị trễ (Dashboard gọn gàng!). / 目前没有任何批次延期（看板整洁！）。")
else:
    st.info("Chưa có dữ liệu lịch xếp hoặc đơn hàng để thực hiện tính toán bảng cảnh báo. / 暂无排程数据或订单数据以进行预警计算。")

# =========================
# DISPLAY SCHEDULE
# =========================
st.markdown("---")
if not st.session_state.df_matrix_schedule.empty:

    st.subheader("📅 Production Schedule / 生产排程表")

    st.dataframe(
        style_matrix(st.session_state.df_matrix_schedule),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📥 Export Excel / 导出 Excel")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.df_matrix_schedule.to_excel(writer, index=False, sheet_name="Schedule")

    st.download_button(
        "💾 Download Excel / 下载 Excel",
        data=output.getvalue(),
        file_name=f"Production_Schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
