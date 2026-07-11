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

# ========================= #
# 2. INPUT & DATA PROCESSING #
# ========================= #
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

# ========================= #
# 3. GENERATE (APPEND-ONLY FIXED WITH CURRENT LOGIC) #
# ========================= #
if st.button("🚀 Generate / Refresh Schedule"):
    start_planning_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    old_df = st.session_state.df_raw_schedule_history.copy()
    
    # ========================= #
    # KEY FIX 1: lấy lịch cũ #
    # ========================= #
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
    
    # ========================= #
    # KEY FIX 2: CHỈ ADD ORDER MỚI HOẶC ORDER ĐÃ ĐƯỢC THAY ĐỔI TỒN KHO TÍNH TOÁN LẠI #
    # ========================= #
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

    # ========================= #
    # MERGE OLD + NEW (NO OVERWRITE) #
    # ========================= #
    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new["Date_Obj"] = pd.to_datetime(df_new["Date_Obj"])
        df_all = pd.concat([old_df, df_new], ignore_index=True)
    else:
        df_all = old_df
        
    df_all = df_all.sort_values(["SỐ MÁY", "SEQ"]).reset_index(drop=True)
    st.session_state.df_raw_schedule_history = df_all.copy()

    # ========================= #
    # MATRIX BUILD #
    # ========================= #
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

    lots = [
        str(x) for x in values
        if str(x) not in ["nan", "None", "", "SỐ MÁY", "Thuộc tính"]
    ]

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
        },
        {
            "selector": "table",
            "props": [
                ("border-collapse", "collapse"),
                ("width", "100%")
            ]
        }
    ])

    return styled


# =========================
# 5. DISPLAY & BẢNG PHỤ TRẠNG THÁI
# =========================

col_main, col_sub = st.columns([2, 1])

with col_main:

    if not st.session_state.df_matrix_schedule.empty:

        st.subheader("🗓️ CHÍNH: LỊCH SẢN XUẤT PHÂN BỔ TRÊN MÁY")

        st.dataframe(
            style_matrix(st.session_state.df_matrix_schedule),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "Chưa có dữ liệu ma trận lịch trình. "
            "Vui lòng bấm 'Generate / Refresh Schedule'."
        )


with col_sub:

    st.subheader("📊 PHỤ: TRẠNG THÁI CHI TIẾT TỪNG LÔ")

    if (
        not st.session_state.df_raw_schedule_history.empty
        and not df_orders.empty
    ):

        df_history = st.session_state.df_raw_schedule_history.copy()

        df_end_date = (
            df_history
            .groupby(
                ["SỐ MÁY", "SỐ LÔ", "MÃ HÀNG"],
                as_index=False
            )["Date_Obj"]
            .max()
        )

        df_end_date.rename(
            columns={
                "Date_Obj": "NGÀY HOÀN THÀNH THỰC TẾ"
            },
            inplace=True
        )


        df_status = pd.merge(
            df_orders[
                [
                    "SỐ MÁY",
                    "SỐ LÔ",
                    "MÃ HÀNG",
                    "NGÀY GIAO",
                    "SL ĐẶT",
                    "TỒN KHO"
                ]
            ],
            df_end_date,
            on=[
                "SỐ MÁY",
                "SỐ LÔ",
                "MÃ HÀNG"
            ],
            how="left"
        )


        def check_status(row):

            if pd.isna(row["NGÀY HOÀN THÀNH THỰC TẾ"]):

                if (
                    row["SL ĐẶT"] - row["TỒN KHO"]
                ) <= 0:
                    return "🟢 Đủ Tồn Kho (OK)"

                return "⚪ Chưa sắp lịch"


            date_real = pd.to_datetime(
                row["NGÀY HOÀN THÀNH THỰC TẾ"]
            ).date()


            date_delivery = (
                pd.to_datetime(row["NGÀY GIAO"]).date()
                if not pd.isna(row["NGÀY GIAO"])
                else None
            )


            if date_delivery and date_real > date_delivery:

                return (
                    f"🔴 Lô {row['SỐ LÔ']} trễ "
                    f"({(date_real - date_delivery).days} ngày)"
                )

            else:

                return f"🟢 Lô {row['SỐ LÔ']} ok"



        df_status["TRẠNG THÁI"] = df_status.apply(
            check_status,
            axis=1
        )


        df_status["NGÀY GIAO"] = (
            df_status["NGÀY GIAO"]
            .dt.strftime("%d/%m/%Y")
            .fillna("Chưa có")
        )


        df_status["NGÀY HOÀN THÀNH THỰC TẾ"] = (
            pd.to_datetime(
                df_status["NGÀY HOÀN THÀNH THỰC TẾ"]
            )
            .dt.strftime("%d/%m/%Y")
            .fillna("-")
        )


        df_display_status = df_status[
            [
                "SỐ MÁY",
                "SỐ LÔ",
                "MÃ HÀNG",
                "TRẠNG THÁI"
            ]
        ]


        def style_status_rows(val):

            if "🔴" in str(val):
                return (
                    "background-color: #ffcccc;"
                    "color: #cc0000;"
                    "font-weight: bold;"
                )

            elif "🟢" in str(val):
                return (
                    "background-color: #e2f0d9;"
                    "color: #385723;"
                )

            return ""


        styled_sub_table = (
            df_display_status.style
            .apply(
                lambda x: [
                    style_status_rows(v)
                    for v in x
                ],
                subset=["TRẠNG THÁI"]
            )
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#2f5597"),
                        ("color", "white"),
                        ("font-weight", "bold")
                    ]
                },
                {
                    "selector": "td",
                    "props": [
                        ("border", "1px solid #ccc"),
                        ("padding", "5px")
                    ]
                }
            ])
        )


        st.dataframe(
            styled_sub_table,
            use_container_width=True,
            hide_index=True
        )


    else:

        st.info(
            "Hệ thống chưa có đủ lịch trình "
            "để phân tích trạng thái các lô."
        )
