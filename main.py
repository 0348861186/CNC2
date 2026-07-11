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

# RESET
if st.sidebar.button("🗑️ Reset Lịch Sử Schedule"):
    st.session_state.df_matrix_schedule = pd.DataFrame()
    st.session_state.df_raw_schedule_history = pd.DataFrame(
        columns=["SỐ MÁY", "Date_Obj", "SỐ LÔ", "MÃ HÀNG", "NĂNG SUẤT", "SEQ"]
    )
    st.sidebar.success("Đã xóa lịch cũ!")
    st.rerun()

# =========================
# 2. INPUT
# =========================
st.sidebar.header("⚙ INPUT")
uploaded_file = st.sidebar.file_uploader("📂 Load đơn hàng", type=["xlsx"])

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
    st.warning("Chưa có dữ liệu đơn hàng.")
    st.stop()

# =========================
# 3. GENERATE (APPEND-ONLY FIXED)
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
            key = (r["SỐ MÁY"], r["SỐ LÔ"], r["MÃ HÀNG"])
            existing_keys.add(key)

            m = r["SỐ MÁY"]
            machine_last_date[m] = max(machine_last_date.get(m, r["Date_Obj"]), r["Date_Obj"])
            machine_seq[m] = max(machine_seq.get(m, 0), int(r["SEQ"]))

        # tiếp nối ngày (KHÔNG gap)
        for m in machine_last_date:
            machine_last_date[m] = machine_last_date[m] + timedelta(days=1)

    new_records = []

    # =========================
    # KEY FIX 2: CHỈ ADD ORDER MỚI
    # =========================
    for _, row in df_orders.iterrows():

        machine = row["SỐ MÁY"]
        lot = row["SỐ LÔ"]
        item = row["MÃ HÀNG"]

        if pd.isna(machine) or machine == "":
            continue

        key = (machine, lot, item)

        # ❌ đã có trong lịch → bỏ qua (KHÔNG regenerate)
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

    # =========================
    # MERGE OLD + NEW (NO OVERWRITE)
    # =========================
    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new["Date_Obj"] = pd.to_datetime(df_new["Date_Obj"])

        df_all = pd.concat([old_df, df_new], ignore_index=True)
    else:
        df_all = old_df

    df_all = df_all.sort_values(["SỐ MÁY", "SEQ"]).reset_index(drop=True)

    st.session_state.df_raw_schedule_history = df_all.copy()

    # =========================
    # MATRIX BUILD
    # =========================
    final_rows = []

    for machine_id, group in df_all.groupby("SỐ MÁY"):

        group = group.sort_values("SEQ")

        row_ngay = {"SỐ MÁY": machine_id, "Thuộc tính": "LỊCH"}
        row_lo = {"SỐ MÁY": machine_id, "Thuộc tính": "SỐ LÔ"}
        row_hang = {"SỐ MÁY": machine_id, "Thuộc tính": "MÃ HÀNG"}
        row_ns = {"SỐ MÁY": machine_id, "Thuộc tính": "NS"}

        for _, r in group.iterrows():
            col = f"C{int(r['SEQ'])}"
            row_ngay[col] = r["Date_Obj"].strftime("%d/%m")
            row_lo[col] = r["SỐ LÔ"]
            row_hang[col] = r["MÃ HÀNG"]
            row_ns[col] = int(r["NĂNG SUẤT"])

        final_rows.extend([row_ngay, row_lo, row_hang, row_ns])

    st.session_state.df_matrix_schedule = pd.DataFrame(final_rows)
    st.success("🎉 Schedule updated (append mode)")

# =========================
# 4. STYLE (BORDER + CENTER + PROFESSIONAL)
# =========================
def style_matrix(df):

    lot_colors = {}

    values = df.values.flatten()
    lots = [str(x) for x in values if str(x) not in ["nan", "None", "", "SỐ MÁY", "Thuộc tính"]]
    lots = list(dict.fromkeys(lots))

    cmap = plt.get_cmap("tab20")

    for i, lot in enumerate(lots):
        lot_colors[lot] = mcolors.rgb2hex(cmap(i % 20))

    def color_row(row):
        return [
            f"background-color: {lot_colors.get(str(v), '')}"
            if str(v) in lot_colors else ""
            for v in row
        ]

    styled = df.style.apply(color_row, axis=1)

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
# 5. DISPLAY
# =========================
if not st.session_state.df_matrix_schedule.empty:

    st.subheader("🗓️ LỊCH SẢN XUẤT")

    st.dataframe(
        style_matrix(st.session_state.df_matrix_schedule),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📥 Xuất Excel")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.df_matrix_schedule.to_excel(writer, index=False, sheet_name="LichSanXuat")

    st.download_button(
        "💾 Tải Excel",
        data=output.getvalue(),
        file_name=f"Lich_San_Xuat_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


