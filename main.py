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
if st.sidebar.button("🗑️ Reset Schedule History"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.sidebar.success("Schedule history cleared!")
    st.rerun()

# =========================
# INPUT (ĐÃ NÂNG CẤP THÊM NÚT LOAD FILE TỒN KHO)
# =========================
st.sidebar.header("⚙ INPUT")
uploaded_file = st.sidebar.file_uploader("📂 Upload Order File", type=["xlsx"])
uploaded_inventory = st.sidebar.file_uploader("📂 Upload Inventory File", type=["xlsx"])

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

def load_inventory(file):
    if file is None:
        return pd.DataFrame()
    df = pd.read_excel(file)
    # Chuẩn hóa tên cột viết hoa loại bỏ khoảng trắng thừa để đối chiếu chính xác
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

df_orders = load_orders(uploaded_file)
df_inventory = load_inventory(uploaded_inventory)

# Tự động cập nhật số lượng TỒN KHO mới từ file tồn kho vào danh sách đơn hàng (nếu có)
if not df_orders.empty and not df_inventory.empty:
    inv_code_col = [c for c in df_inventory.columns if "MÃ HÀNG" in c or "MA HANG" in c]
    inv_qty_col = [c for c in df_inventory.columns if "TỒN KHO" in c or "TON KHO" in c or "SL" in c]
    
    if inv_code_col and inv_qty_col:
        # Tạo từ điển map giữa Mã Hàng -> Số lượng tồn kho
        inv_map = df_inventory.set_index(inv_code_col[0])[inv_qty_col[0]].to_dict()
        df_orders["TỒN KHO"] = df_orders["MÃ HÀNG"].map(inv_map).fillna(df_orders["TỒN KHO"])
        df_orders["TỒN KHO"] = pd.to_numeric(df_orders["TỒN KHO"], errors="coerce").fillna(0)

if df_orders.empty:
    st.warning("No order data available.")
    st.stop()

# =========================
# GENERATE (LOGIC GỐC KHÔNG ĐỔI)
# =========================
if st.button("🚀 Generate / Refresh Schedule"):

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
    st.success("Schedule updated successfully")

# =========================
# STYLE (MACHINE + LOT COLOR FIXED)
# =========================
def style_matrix(df):

    cmap = plt.get_cmap("tab20")

    color_map = {}
    color_index = 0

    for machine in df["SỐ MÁY"].unique():

        lot_row = df[(df["SỐ MÁY"] == machine) & (df["Attribute"] == "LOT")]

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
        machine = row["SỐ MÁY"]
        colors = []

        for col in row.index:

            if col in ["SỐ MÁY", "Attribute"]:
                colors.append("")
                continue

            lot_val = df.loc[
                (df["SỐ MÁY"] == machine) &
                (df["Attribute"] == "LOT"),
                col
            ].values

            lot_val = str(lot_val[0]) if len(lot_val) > 0 else ""

            colors.append(f"background-color: {get_color(machine, lot_val)}")

        return colors

    styled = df.style.apply(apply_color, axis=1)

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
# DISPLAY & BẢNG TRẠNG THÁI (ĐÃ NÂNG CẤP THEO YÊU CẦU 2)
# =========================
if not st.session_state.df_matrix_schedule.empty:

    # --- XỬ LÝ BẢNG TRẠNG THÁI TIẾN ĐỘ ---
    st.subheader("⚠️ BẢNG TRẠNG THÁI TIẾN ĐỘ")
    
    df_raw = st.session_state.df_raw_schedule_history
    
    if not df_raw.empty and not df_orders.empty:
        # Lấy ngày hoàn thành thực tế cuối cùng (Max Date) cho từng Số Lô từ lịch sản xuất
        df_finish = df_raw.groupby("SỐ LÔ")["Date_Obj"].max().reset_index()
        df_finish.columns = ["SỐ LÔ", "NGÀY HOÀN THÀNH THỰC TẾ"]
        
        # Kết hợp với thông tin đơn hàng để lấy Ngày Giao dự kiến gốc
        df_check = pd.merge(df_orders[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO"]].drop_duplicates("SỐ LÔ"), df_finish, on="SỐ LÔ", how="inner")
        
        # Tính số ngày trễ
        df_check["TRỄ (NGÀY)"] = (df_check["NGÀY HOÀN THÀNH THỰC TẾ"] - df_check["NGÀY GIAO"]).dt.days
        
        # Chỉ lọc ra các lô thực sự bị trễ tiến độ
        df_delay = df_check[df_check["TRỄ (NGÀY)"] > 0].copy()
        
        if not df_delay.empty:
            df_delay["NGÀY GIAO"] = df_delay["NGÀY GIAO"].dt.strftime("%d/%m/%Y")
            df_delay["NGÀY HOÀN THÀNH THỰC TẾ"] = df_delay["NGÀY HOÀN THÀNH THỰC TẾ"].dt.strftime("%d/%m/%Y")
            
            st.error("🚨 PHÁT HIỆN CÁC LÔ HÀNG BỊ TRỄ TIẾN ĐỘ XUẤT HÀNG LÀM THEO KẾ HOẠCH MỚI")
            st.dataframe(
                df_delay[["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG", "NGÀY GIAO", "NGÀY HOÀN THÀNH THỰC TẾ", "TRỄ (NGÀY)"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            # Nếu không có đơn nào bị trễ thì chỉ in dòng chữ thông báo duy nhất
            st.success("🎉 TẤT CẢ ĐƠN HÀNG KỊP XUẤT")
    else:
        st.info("Chưa có dữ liệu tiến độ để phân tích.")

    st.markdown("---")

    # --- HIỂN THỊ LỊCH SẢN XUẤT CHÍNH ---
    st.subheader("📅 Production Schedule")

    st.dataframe(
        style_matrix(st.session_state.df_matrix_schedule),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📥 Export Excel")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.df_matrix_schedule.to_excel(writer, index=False, sheet_name="Schedule")

    st.download_button(
        "💾 Download Excel",
        data=output.getvalue(),
        file_name=f"Production_Schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
