import math

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vessel Meeting Detection System", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background: #f7f9fc; }
    [data-testid="stSidebar"] { background: #10243e; }
    [data-testid="stSidebar"] * { color: #eef5ff !important; }
    .hero { padding: 1.2rem 1.5rem; border-radius: 16px; background: linear-gradient(115deg,#10243e,#1b4d6b); color: white; margin-bottom: 1rem; }
    .hero h1 { color: white; margin: 0 0 .25rem; font-size: 2.15rem; }
    .hero p { color: #c9deef; margin: 0; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e4eaf1; padding: 14px 16px; border-radius: 12px; box-shadow: 0 3px 12px rgba(16,36,62,.06); }
    .section-title { color:#10243e; font-size:1.25rem; font-weight:700; margin:1rem 0 .5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>⚓ Vessel Meeting Detection System</h1>
  <p>Geospatial analysis for identifying vessel encounters within configurable distance, time and speed parameters.</p>
</div>
""", unsafe_allow_html=True)

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
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin1")
    return pd.read_excel(uploaded_file)


def meeting_status(duration_min, detection_count, min_duration_min, min_points_confirmed):
    if duration_min >= min_duration_min and detection_count >= min_points_confirmed:
        return "Confirmed"
    if duration_min >= min_duration_min:
        return "Possible"
    return "Below Duration"


# -----------------------------
# Sidebar settings
# -----------------------------
st.sidebar.header("Setting Detection")

distance_threshold = st.sidebar.number_input(
    "Jarak maksimum (meter)", min_value=10, max_value=1000, value=100, step=10
)

min_duration_min = st.sidebar.number_input(
    "Minimum duration meeting (minit)", min_value=1, max_value=1440, value=10, step=1
)

# Ini bukan duration meeting.
# Ini cuma tolerance sebab timestamp AIS antara kapal kadang-kadang tak sama tepat.
ais_time_tolerance_min = st.sidebar.number_input(
    "AIS time tolerance / beza masa rekod (minit)",
    min_value=1,
    max_value=120,
    value=30,
    step=1,
)

speed_threshold = st.sidebar.number_input(
    "Speed maksimum (knot)", min_value=0.0, max_value=20.0, value=1.0, step=0.1
)

min_points_confirmed = st.sidebar.number_input(
    "Minimum detection untuk Confirmed", min_value=1, max_value=10, value=2, step=1
)

uploaded_file = st.file_uploader("Upload vessel data (CSV atau XLSX)", type=["csv", "xlsx"])

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

st.markdown('<div class="section-title">Dataset Overview</div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total records", f"{len(df):,}")
m2.metric("Total columns", f"{len(df.columns):,}")
m3.metric("File type", uploaded_file.name.split('.')[-1].upper())
m4.metric("Detection range", f"{distance_threshold:,.0f} m")

with st.expander("Preview uploaded data", expanded=False):
    st.dataframe(df.head(20), use_container_width=True, height=320)

cols = list(df.columns)

st.markdown('<div class="section-title">Map Data Columns</div>', unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    default_time = find_default_column(cols, ["local time", "utc time", "time", "date"])
    time_col = st.selectbox(
        "Column Masa",
        cols,
        index=cols.index(default_time) if default_time in cols else 0,
    )

with col2:
    default_vessel = find_default_column(cols, ["name", "vessel", "ship", "mmsi"])
    vessel_col = st.selectbox(
        "Column Kapal",
        cols,
        index=cols.index(default_vessel) if default_vessel in cols else 0,
    )

with col3:
    default_lat = find_default_column(cols, ["latitude", "lat"])
    lat_col = st.selectbox(
        "Column Latitude",
        cols,
        index=cols.index(default_lat) if default_lat in cols else 0,
    )

with col4:
    default_lon = find_default_column(cols, ["longitude", "lon", "lng"])
    lon_col = st.selectbox(
        "Column Longitude",
        cols,
        index=cols.index(default_lon) if default_lon in cols else 0,
    )

with col5:
    default_speed = find_default_column(cols, ["sog", "speed"])
    speed_options = ["Tiada"] + cols
    speed_col = st.selectbox(
        "Column Speed/SOG",
        speed_options,
        index=speed_options.index(default_speed) if default_speed in speed_options else 0,
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

st.markdown('<div class="section-title">Area Filter</div>', unsafe_allow_html=True)
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
        (work[lat_col] >= min_lat)
        & (work[lat_col] <= max_lat)
        & (work[lon_col] >= min_lon)
        & (work[lon_col] <= max_lon)
    ]

st.info(f"{len(work):,} records ready for detection", icon="📍")

# -----------------------------
# Detection process
# -----------------------------
if st.button("Run vessel detection", type="primary", use_container_width=True):
    if len(work) < 2:
        st.warning("Data kurang dari 2 row. Tak boleh compare vessel.")
        st.stop()

    work = work.sort_values(time_col).reset_index(drop=True)
    records = work.to_dict("records")

    detections = []
    ais_tolerance = pd.Timedelta(minutes=ais_time_tolerance_min)

    # Compare row by row.
    # Kita masih guna AIS tolerance supaya tak compare lokasi kapal yang beza masa terlalu jauh.
    for i in range(len(records)):
        r1 = records[i]
        t1 = r1[time_col]
        v1 = str(r1[vessel_col]).strip()

        for j in range(i + 1, len(records)):
            r2 = records[j]
            t2 = r2[time_col]

            # Stop bila beza masa rekod AIS dah lebih tolerance.
            # Contoh tolerance 30 minit: rekod kapal A 10:00 boleh compare dengan kapal B 10:25.
            if t2 - t1 > ais_tolerance:
                break

            v2 = str(r2[vessel_col]).strip()
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
                float(r1[lat_col]),
                float(r1[lon_col]),
                float(r2[lat_col]),
                float(r2[lon_col]),
            )

            if distance_m <= distance_threshold:
                pair = tuple(sorted([v1, v2]))
                detection_time = min(t1, t2)

                detections.append(
                    {
                        "Vessel A": pair[0],
                        "Vessel B": pair[1],
                        "Detection Time": detection_time,
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
                    }
                )

    detail_df = pd.DataFrame(detections)

    if detail_df.empty:
        st.warning("Tiada meeting dikesan ikut setting sekarang.")
        st.stop()

    summary_rows = []

    for (va, vb), g in detail_df.groupby(["Vessel A", "Vessel B"]):
        g = g.sort_values("Detection Time")

        first_seen = g["Detection Time"].min()
        last_seen = g["Detection Time"].max()
        duration_min = round((last_seen - first_seen).total_seconds() / 60, 2)
        detection_count = len(g)
        min_distance = round(g["Distance Meter"].min(), 2)
        avg_distance = round(g["Distance Meter"].mean(), 2)
        max_time_gap = round(g["Time Gap Min"].max(), 2)

        if speed_col != "Tiada":
            avg_speed = round(pd.concat([g["Speed A"], g["Speed B"]]).dropna().mean(), 2)
            max_speed = round(pd.concat([g["Speed A"], g["Speed B"]]).dropna().max(), 2)
        else:
            avg_speed = None
            max_speed = None

        status = meeting_status(
            duration_min,
            detection_count,
            min_duration_min,
            min_points_confirmed,
        )

        summary_rows.append(
            {
                "Vessel A": va,
                "Vessel B": vb,
                "First Seen": first_seen,
                "Last Seen": last_seen,
                "Duration Min": duration_min,
                "Detection Count": detection_count,
                "Min Distance Meter": min_distance,
                "Avg Distance Meter": avg_distance,
                "Avg Speed Knot": avg_speed,
                "Max Speed Knot": max_speed,
                "Max AIS Time Gap Min": max_time_gap,
                "Status": status,
            }
        )

    summary_df = pd.DataFrame(summary_rows)

    # Rule utama user: duration mesti 10 minit dan ke atas.
    summary_df = summary_df[summary_df["Duration Min"] >= min_duration_min]

    if summary_df.empty:
        st.warning("Ada jarak dekat dikesan, tapi tiada yang cukup minimum duration meeting.")
        st.subheader("Raw Detection Detail")
        st.dataframe(detail_df, use_container_width=True)
        st.stop()

    status_order = {"Confirmed": 1, "Possible": 2, "Below Duration": 3}
    summary_df["Status Order"] = summary_df["Status"].map(status_order).fillna(9)
    summary_df = summary_df.sort_values(
        ["Status Order", "Duration Min", "Min Distance Meter"],
        ascending=[True, False, True],
    ).drop(columns=["Status Order"])

    st.markdown('<div class="section-title">Detection Results</div>', unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Confirmed meetings", int((summary_df["Status"] == "Confirmed").sum()))
    r2.metric("Possible meetings", int((summary_df["Status"] == "Possible").sum()))
    r3.metric("Vessel pairs", len(summary_df))
    r4.metric("Closest distance", f"{summary_df['Min Distance Meter'].min():,.1f} m")

    st.subheader("Meeting Summary")
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
