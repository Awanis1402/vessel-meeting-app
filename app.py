import math
from itertools import combinations

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vessel Meeting Detector", layout="wide")

st.title("Vessel Meeting Detector - Fasa 1")
st.caption("Upload CSV/XLSX harian → filter kawasan → detect vessel bertemu ≤100m")

# -----------------------------
# Helper functions
# -----------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    """Calculate distance between 2 lat/lon points in meter."""
    r = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_default_column(cols, keywords):
    lower_map = {c.lower(): c for c in cols}
    for key in keywords:
        for lower, original in lower_map.items():
            if key.lower() in lower:
                return original
    return cols[0] if cols else None


def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # Try normal CSV first, then fallback encoding
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin1")
    return pd.read_excel(uploaded_file)

# -----------------------------
# Sidebar settings
# -----------------------------
st.sidebar.header("Setting Detection")

distance_threshold = st.sidebar.number_input(
    "Jarak maksimum (meter)", min_value=10, max_value=1000, value=100, step=10
)
time_window_min = st.sidebar.number_input(
    "Time window (minit)", min_value=1, max_value=60, value=10, step=1
)
speed_threshold = st.sidebar.number_input(
    "Speed maksimum (knot)", min_value=0.0, max_value=20.0, value=1.0, step=0.1
)
min_points_confirmed = st.sidebar.number_input(
    "Minimum detection untuk Confirmed", min_value=1, max_value=10, value=2, step=1
)

uploaded_file = st.file_uploader("Upload file CSV atau XLSX", type=["csv", "xlsx"])

if uploaded_file is None:
    st.info("Upload CSV/XLSX dulu untuk mula.")
    st.stop()

try:
    df = load_file(uploaded_file)
    df = normalize_columns(df)
except Exception as e:
    st.error(f"File tak boleh dibaca: {e}")
    st.stop()

if df.empty:
    st.warning("File kosong.")
    st.stop()

st.subheader("Preview Data")
st.dataframe(df.head(20), use_container_width=True)

cols = list(df.columns)

st.subheader("Pilih Column")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    time_col = st.selectbox(
        "Column Masa",
        cols,
        index=cols.index(find_default_column(cols, ["local time", "utc time", "time", "date"]))
        if find_default_column(cols, ["local time", "utc time", "time", "date"]) in cols else 0,
    )
with col2:
    vessel_col = st.selectbox(
        "Column Kapal",
        cols,
        index=cols.index(find_default_column(cols, ["name", "vessel", "ship", "mmsi"]))
        if find_default_column(cols, ["name", "vessel", "ship", "mmsi"]) in cols else 0,
    )
with col3:
    lat_col = st.selectbox(
        "Column Latitude",
        cols,
        index=cols.index(find_default_column(cols, ["latitude", "lat"]))
        if find_default_column(cols, ["latitude", "lat"]) in cols else 0,
    )
with col4:
    lon_col = st.selectbox(
        "Column Longitude",
        cols,
        index=cols.index(find_default_column(cols, ["longitude", "lon", "lng"]))
        if find_default_column(cols, ["longitude", "lon", "lng"]) in cols else 0,
    )
with col5:
    speed_col = st.selectbox(
        "Column Speed/SOG",
        ["Tiada"] + cols,
        index=(["Tiada"] + cols).index(find_default_column(cols, ["sog", "speed"]))
        if find_default_column(cols, ["sog", "speed"]) in cols else 0,
    )

work = df.copy()

# Clean selected columns
work[time_col] = pd.to_datetime(work[time_col], errors="coerce")
work[lat_col] = pd.to_numeric(work[lat_col], errors="coerce")
work[lon_col] = pd.to_numeric(work[lon_col], errors="coerce")

if speed_col != "Tiada":
    work[speed_col] = pd.to_numeric(work[speed_col], errors="coerce")

work = work.dropna(subset=[time_col, vessel_col, lat_col, lon_col])

if work.empty:
    st.error("Data tak cukup selepas cleaning. Check column masa/kapal/lat/lon.")
    st.stop()

st.subheader("Filter Kawasan")
min_lat_data = float(work[lat_col].min())
max_lat_data = float(work[lat_col].max())
min_lon_data = float(work[lon_col].min())
max_lon_data = float(work[lon_col].max())

area_filter = st.checkbox("Aktifkan filter kawasan tertentu", value=False)

if area_filter:
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        min_lat = st.number_input("Min Latitude", value=min_lat_data, format="%.6f")
    with a2:
        max_lat = st.number_input("Max Latitude", value=max_lat_data, format="%.6f")
    with a3:
        min_lon = st.number_input("Min Longitude", value=min_lon_data, format="%.6f")
    with a4:
        max_lon = st.number_input("Max Longitude", value=max_lon_data, format="%.6f")

    work = work[
        (work[lat_col] >= min_lat) &
        (work[lat_col] <= max_lat) &
        (work[lon_col] >= min_lon) &
        (work[lon_col] <= max_lon)
    ]

st.write(f"Jumlah row selepas filter: **{len(work):,}**")

if st.button("Process Detection", type="primary"):
    if len(work) < 2:
        st.warning("Data kurang dari 2 row. Tak boleh compare vessel.")
        st.stop()

    work = work.sort_values(time_col).reset_index(drop=True)

    detections = []
    time_window = pd.Timedelta(minutes=time_window_min)

    # Compare pair secara sliding window. Sesuai untuk CSV harian kecil/sederhana.
    records = work.to_dict("records")

    for i in range(len(records)):
        r1 = records[i]
        t1 = r1[time_col]
        v1 = str(r1[vessel_col])

        for j in range(i + 1, len(records)):
            r2 = records[j]
            t2 = r2[time_col]

            if t2 - t1 > time_window:
                break

            v2 = str(r2[vessel_col])
            if v1 == v2:
                continue

            # Speed filter kalau ada column speed
            if speed_col != "Tiada":
                s1 = r1.get(speed_col)
                s2 = r2.get(speed_col)
                if pd.isna(s1) or pd.isna(s2):
                    continue
                if float(s1) > speed_threshold or float(s2) > speed_threshold:
                    continue
            else:
                s1 = None
                s2 = None

            distance_m = haversine_m(
                float(r1[lat_col]), float(r1[lon_col]),
                float(r2[lat_col]), float(r2[lon_col])
            )

            if distance_m <= distance_threshold:
                pair = tuple(sorted([v1, v2]))
                detections.append({
                    "Vessel A": pair[0],
                    "Vessel B": pair[1],
                    "Time A": t1,
                    "Time B": t2,
                    "Time Gap Min": round(abs((t2 - t1).total_seconds()) / 60, 2),
                    "Distance Meter": round(distance_m, 2),
                    "Lat A": r1[lat_col],
                    "Lon A": r1[lon_col],
                    "Lat B": r2[lat_col],
                    "Lon B": r2[lon_col],
                    "Speed A": round(float(s1), 2) if s1 is not None else None,
                    "Speed B": round(float(s2), 2) if s2 is not None else None,
                })

    detail_df = pd.DataFrame(detections)

    if detail_df.empty:
        st.warning("Tiada meeting dikesan ikut setting sekarang.")
        st.stop()

    summary_rows = []
    for (va, vb), g in detail_df.groupby(["Vessel A", "Vessel B"]):
        first_seen = min(g["Time A"].min(), g["Time B"].min())
        last_seen = max(g["Time A"].max(), g["Time B"].max())
        duration_min = round((last_seen - first_seen).total_seconds() / 60, 2)
        detection_count = len(g)
        min_distance = round(g["Distance Meter"].min(), 2)
        avg_distance = round(g["Distance Meter"].mean(), 2)

        if speed_col != "Tiada":
            avg_speed = round(pd.concat([g["Speed A"], g["Speed B"]]).dropna().mean(), 2)
        else:
            avg_speed = None

        status = "Confirmed" if detection_count >= min_points_confirmed else "Possible"

        summary_rows.append({
            "Vessel A": va,
            "Vessel B": vb,
            "First Seen": first_seen,
            "Last Seen": last_seen,
            "Duration Min": duration_min,
            "Detection Count": detection_count,
            "Min Distance Meter": min_distance,
            "Avg Distance Meter": avg_distance,
            "Avg Speed Knot": avg_speed,
            "Status": status,
        })

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["Status", "Min Distance Meter", "Detection Count"],
        ascending=[True, True, False]
    )

    st.subheader("Summary Meeting")
    st.dataframe(summary_df, use_container_width=True)

    st.download_button(
        "Download Summary CSV",
        summary_df.to_csv(index=False).encode("utf-8"),
        "vessel_meeting_summary.csv",
        "text/csv",
    )

    st.subheader("Raw Detection Detail")
    st.dataframe(detail_df, use_container_width=True)

    st.download_button(
        "Download Detail CSV",
        detail_df.to_csv(index=False).encode("utf-8"),
        "vessel_meeting_detail.csv",
        "text/csv",
    )
