import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =====================================================
# CẤU HÌNH GIAO DIỆN TRANG WEB
# =====================================================
st.set_page_config(layout="wide", page_title="RESILIENT NAVIGATION - FIR HCM VÀ BIỂN ĐÔNG ")

st.markdown(
    "<h2 style='color:#ffffff;font-size:26px;font-weight:800;margin-bottom:4px;'>"
    "🛡️ HỆ THỐNG MÔ PHỎNG RESILIENT NAVIGATION & ỨNG PHÓ KHẨN CẤP</h2>",
    unsafe_allow_html=True
)

# =====================================================
# THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR CONTROLLER)
# =====================================================
st.sidebar.header("🕹️ BỘ ĐIỀU KHIỂN KỊCH BẢN")
scenario = st.sidebar.selectbox(
    "Chọn kịch bản bất ổn an ninh GNSS:",
    [
        "Kịch bản 1: Mất tín hiệu GNSS cục bộ (Jamming)",
        "Kịch bản 2: Tấn công giả mạo tọa độ (Spoofing - Position Jump)",
        "Kịch bản 3: Nhiễu vô tuyến diện rộng & Quản lý luồng (ATFM)"
    ]
)

n_points = 100  # Cố định độ phân giải quỹ đạo
st.sidebar.markdown("---")

# ── Situational Awareness Panel (sidebar) ─────────────────────────────
AWARENESS_DATA = {
    "Kịch bản 1": {
        "aircraft":    "1 tàu bay",
        "notam":       "ADVISORY",
        "notam_color": "#E8A020",
        "elapsed":     "T+01:45",
        "systems": [
            ("GNSS",  "❌", "#D0021B"),
            ("INS",   "✅", "#00A550"),
            ("DME",   "✅", "#00A550"),
            ("Radar", "✅", "#00A550"),
        ],
    },
    "Kịch bản 2": {
        "aircraft":    "1 tàu bay",
        "notam":       "URGENT",
        "notam_color": "#D0021B",
        "elapsed":     "T+00:45",
        "systems": [
            ("GNSS",  "⚠️", "#E8A020"),
            ("INS",   "✅", "#00A550"),
            ("DME",   "✅", "#00A550"),
            ("Radar", "✅", "#00A550"),
        ],
    },
    "Kịch bản 3": {
        "aircraft":    "3 tàu bay",
        "notam":       "URGENT",
        "notam_color": "#D0021B",
        "elapsed":     "T+01:00",
        "systems": [
            ("GNSS",  "❌", "#D0021B"),
            ("INS",   "✅", "#00A550"),
            ("DME",   "✅", "#00A550"),
            ("Radar", "⚠️", "#E8A020"),
        ],
    },
}

_aw_key = (
    "Kịch bản 1" if "Kịch bản 1" in scenario else
    ("Kịch bản 2" if "Kịch bản 2" in scenario else "Kịch bản 3")
)
aw = AWARENESS_DATA[_aw_key]

# Build system status rows
_sys_rows = ""
for s, ic, c in aw["systems"]:
    _sys_rows += (
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"background:#1e2130;border-radius:5px;padding:5px 9px;margin-bottom:4px;'>"
        f"<span style='font-size:12px;font-weight:700;color:#ccd8e8;'>{s}</span>"
        f"<span style='font-size:14px;'>{ic}</span>"
        f"</div>"
    )

_aw_html = (
    "<div style='background:#0d1117;border-radius:8px;padding:12px 14px;'>"

    "<p style='font-size:12px;font-weight:800;color:#7eb3d8;margin:0 0 10px 0;"
    "letter-spacing:.6px;'>🔌 SITUATIONAL AWARENESS</p>"

    "<div style='display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:8px;'>"

    "<div style='background:#1e2130;border-radius:6px;padding:8px 10px;'>"
    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:3px;'>TÀU BAY ẢNH HƯỞNG</div>"
    f"<div style='font-size:15px;font-weight:800;color:#ffffff;'>{aw['aircraft']}</div>"
    "</div>"

    "<div style='background:#1e2130;border-radius:6px;padding:8px 10px;'>"
    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:3px;'>THỜI GIAN</div>"
    f"<div style='font-size:15px;font-weight:800;color:#ffffff;font-family:monospace;'>{aw['elapsed']}</div>"
    "</div>"

    "</div>"

    "<div style='background:#1e2130;border-radius:6px;padding:8px 10px;margin-bottom:9px;'>"
    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:4px;'>MỨC ĐỘ NOTAM</div>"
    f"<div style='font-size:14px;font-weight:800;color:{aw['notam_color']};'>⚠ {aw['notam']}</div>"
    "</div>"

    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:5px;'>TRẠNG THÁI HỆ THỐNG</div>"
    + _sys_rows +
    "</div>"
)

st.sidebar.markdown(_aw_html, unsafe_allow_html=True)

# Tên kịch bản động nằm ngay dưới tiêu đề chính (đặt sau sidebar để scenario đã được định nghĩa)
_scenario_labels = {
    "Kịch bản 1": ("🔶", "#E8A020", "Kịch bản 1 — Mất tín hiệu GNSS cục bộ (Jamming)"),
    "Kịch bản 2": ("🔴", "#D0021B", "Kịch bản 2 — Tấn công giả mạo tọa độ (Spoofing)"),
    "Kịch bản 3": ("🔥", "#c0392b", "Kịch bản 3 — Nhiễu diện rộng & Quản lý luồng (ATFM)"),
}
for _key, (_icon, _color, _label) in _scenario_labels.items():
    if _key in scenario:
        st.markdown(
            f"<p style='font-size:21px;font-weight:800;color:{_color};"
            f"margin:0 0 2px 0;letter-spacing:0.3px;'>{_icon} {_label}</p>",
            unsafe_allow_html=True
        )
        break

st.markdown("<hr style='border:1px solid #334;margin:6px 0 10px 0;'>", unsafe_allow_html=True)

np.random.seed(42)

# =====================================================
# ĐỊNH NGHĨA DỮ LIỆU ĐƯỜNG BAY GỐC (BASE TRAJECTORIES)
# =====================================================
# Hàm nội suy tọa độ qua chuỗi nhiều Waypoint chuyển hệ Độ-Phút sang Thập phân
def chuyển_độ_phút_sang_thập_phân(độ, phút):
    return độ + (phút / 60.0)

# Chuỗi tọa độ thực tế trích xuất từ hình ảnh ảnh (VVTS -> MOXEB -> NIXIV -> ESPOB -> ELALO -> WSSS)
waypoints_route1 = [
    (chuyển_độ_phút_sang_thập_phân(10, 49.74), chuyển_độ_phút_sang_thập_phân(106, 39.12)),  # VVTS / MOXEB
    (chuyển_độ_phút_sang_thập_phân(9, 24.30),  chuyển_độ_phút_sang_thập_phân(106, 37.80)),  # NIXIV
    (chuyển_độ_phút_sang_thập_phân(7, 0.98),   chuyển_độ_phút_sang_thập_phân(105, 31.78)),  # ESPOB
    (chuyển_độ_phút_sang_thập_phân(4, 13.72),  chuyển_độ_phút_sang_thập_phân(104, 34.11)),  # ELALO
    (chuyển_độ_phút_sang_thập_phân(1, 22.55),  chuyển_độ_phút_sang_thập_phân(103, 59.17))   # OMKOM / WSSS
]

# Chia đều số lượng `n_points` (100 điểm) dọc theo các chặng waypoint
lats_wps, lons_wps = zip(*waypoints_route1)
chặng_vết = np.linspace(0, 1, len(waypoints_route1))
mốc_nội_suy = np.linspace(0, 1, n_points)

t_lat1 = np.interp(mốc_nội_suy, chặng_vết, lats_wps)
t_lon1 = np.interp(mốc_nội_suy, chặng_vết, lons_wps)

PNH_LAT, PNH_LON = 11.546, 104.844
KUL_LAT, KUL_LON = 2.745, 101.709
t_lat2 = np.linspace(PNH_LAT, KUL_LAT, n_points)
t_lon2 = np.linspace(PNH_LON, KUL_LON, n_points)

BKK_LAT, BKK_LON = 13.690, 100.750
CGK_LAT, CGK_LON = -6.126, 106.656
t_lat3 = np.linspace(BKK_LAT, CGK_LAT, n_points)
t_lon3 = np.linspace(BKK_LON, CGK_LON, n_points)

# =====================================================
# XỬ LÝ LOGIC TOÁN HỌC VÀ ĐÓNG GÓI ANIMATION FRAMES
# =====================================================

frames = []
fig_map = go.Figure()

# ─────────────────────────────────────────────────────
# KỊCH BẢN 1: JAMMING — Mất tín hiệu GNSS cục bộ
# ─────────────────────────────────────────────────────
if "Kịch bản 1" in scenario:
    # Vùng nhiễu (bounding box)
    z_lat = [5.5, 5.5, 8.5, 8.5, 5.5]
    z_lon = [104.2, 106.5, 106.5, 104.2, 104.2]

    # GNSS bị đóng băng tại chỗ trong vùng nhiễu
    g_lat1, g_lon1 = t_lat1.copy(), t_lon1.copy()
    g_lat1[40:70] = t_lat1[39]
    g_lon1[40:70] = t_lon1[39]

    # Resilient Navigation: INS/DME — giả lập drift tích lũy thực tế (tối đa ~2-3 NM)
    r_lat1, r_lon1 = t_lat1.copy(), t_lon1.copy()
    
    # Tạo độ lệch drift mượt mà tăng dần theo thời gian thay vì random quá nặng
    drift_profile = np.linspace(0, 0.03, 30) 
    r_lat1[40:70] += drift_profile * 0.5
    r_lon1[40:70] += drift_profile * 0.5

    # ĐÃ SỬA: Tính sai số thực tế dựa trên hệ thống dự phòng INS (r_lat1) vs Thực tế (t_lat1)
    error_array = np.zeros(n_points)
    mean_lat_j = (r_lat1[40:70] + t_lat1[40:70]) / 2
    dlat_nm_j = (r_lat1[40:70] - t_lat1[40:70]) * 60
    dlon_nm_j = (r_lon1[40:70] - t_lon1[40:70]) * 60 * np.cos(np.radians(mean_lat_j))
    
    # Sai số tích lũy của INS sẽ chỉ rơi vào khoảng 0.5 - 2.5 NM (Rất chuẩn thực tế)
    error_array[40:70] = np.sqrt(dlat_nm_j**2 + dlon_nm_j**2)

    # Animation Frames
    for i in range(2, n_points):
        frames.append(go.Frame(data=[
            go.Scattermapbox(lat=t_lat1[:i], lon=t_lon1[:i], mode='lines', line=dict(color='green', width=3)),
            go.Scattermapbox(lat=g_lat1[:i], lon=g_lon1[:i], mode='markers+lines', marker=dict(size=4, color='orange')),
            go.Scattermapbox(lat=r_lat1[:i], lon=r_lon1[:i], mode='lines', line=dict(color='blue', width=4)),
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,165,0,0.06)', line=dict(color='orange', width=2)),
        ], name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat1[:2], lon=t_lon1[:2], mode='lines', line=dict(color='green', width=3), name='Vết Radar PSR/SSR (Thực tế)'))
    fig_map.add_trace(go.Scattermapbox(lat=g_lat1[:2], lon=g_lon1[:2], mode='markers+lines', marker=dict(size=4, color='orange'), name='Tín hiệu Định vị GNSS (Bị đóng băng)'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat1[:2], lon=r_lon1[:2], mode='lines', line=dict(color='blue', width=4), name='Tích hợp Dự Phòng (INS/DME)'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,165,0,0.06)', line=dict(color='orange', width=2), name='Vùng Nhiễu GNSS Cục Bộ'))

    status_text = "🟢 **ATC Response:** Hệ thống phát hiện mất tính toàn vẹn vệ tinh trên đường bay. Chuyển sang giám sát PSR/SSR và chế độ dự phòng INS/DME."

# ─────────────────────────────────────────────────────
# KỊCH BẢN 2: SPOOFING — Giả mạo tọa độ (Position Jump)
# ─────────────────────────────────────────────────────
elif "Kịch bản 2" in scenario:
    # Vùng tấn công
    z_lat = [4.5, 4.5, 8.5, 8.5, 4.5]
    z_lon = [104.0, 106.2, 106.2, 104.0, 104.0]

    # GNSS bị giả mạo — tọa độ nhảy loạn (Tín hiệu đầu vào lỗi)
    g_lat1, g_lon1 = t_lat1.copy(), t_lon1.copy()
    g_lat1[40:70] += 0.45 * np.random.normal(size=30)
    g_lon1[40:70] += 0.45 * np.random.normal(size=30)

    # Resilient Navigation: FDE (Fault Detection & Exclusion) — rolling average
    # Làm mượt để loại bỏ các điểm nhảy (giả lập thuật toán lọc máy tính onboard)
    r_lat1 = pd.Series(g_lat1).rolling(window=10, center=True, min_periods=1).mean().values.copy()
    r_lon1 = pd.Series(g_lon1).rolling(window=10, center=True, min_periods=1).mean().values.copy()
    # Ép các điểm từ 0 đến 35 (trước khi gặp nhiễu) bằng chuẩn tọa độ thực tế
    r_lat1[:35] = t_lat1[:35]
    r_lon1[:35] = t_lon1[:35]

    # Giả định sau điểm thứ 85 (hoặc 90 tùy n_points), hệ thống đã phục hồi hoàn toàn
    r_lat1[85:] = t_lat1[85:]
    r_lon1[85:] = t_lon1[85:]

    # ĐÃ SỬA: Tính sai số của hệ thống sau khi ĐÃ KHÁNG NHIỄU (r_lat1) vs Thực tế (t_lat1)
    mean_lat_s = (r_lat1 + t_lat1) / 2
    dlat_nm_s = (r_lat1 - t_lat1) * 60
    dlon_nm_s = (r_lon1 - t_lon1) * 60 * np.cos(np.radians(mean_lat_s))
    error_array = np.sqrt(dlat_nm_s**2 + dlon_nm_s**2)

    # Animation Frames
    for i in range(2, n_points):
        frames.append(go.Frame(data=[
            go.Scattermapbox(lat=t_lat1[:i], lon=t_lon1[:i], mode='lines', line=dict(color='green', width=3)),
            go.Scattermapbox(lat=g_lat1[40:max(41, i)] if i > 40 else [None], lon=g_lon1[40:max(41, i)] if i > 40 else [None], mode='markers', marker=dict(size=5, color='red')),
            go.Scattermapbox(lat=r_lat1[:i], lon=r_lon1[:i], mode='lines', line=dict(color='blue', width=4)),
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.06)', line=dict(color='red', width=2)),
        ], name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat1[:2], lon=t_lon1[:2], mode='lines', line=dict(color='green', width=3), name='Vết Radar PSR/SSR (Thực tế)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='markers', marker=dict(size=5, color='red'), name='Tọa độ Giả mạo (Spoofing)'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat1[:2], lon=r_lon1[:2], mode='lines', line=dict(color='blue', width=4), name='Xử lý Kháng nhiễu FDE (INS/DME)'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.06)', line=dict(color='red', width=2), name='Vùng Tấn Công Giả Mạo'))

    status_text = "🚨 **ATC Response:** Phát hiện sai lệch lớn giữa vết Radar và báo cáo tọa độ ADS-B của tàu bay. Lập tức phát lệnh yêu cầu tổ lái cô lập máy thu GPS, chuyển sang khai thác INS thủ công."

# ─────────────────────────────────────────────────────
# KỊCH BẢN 3: ATFM — Nhiễu diện rộng, nhiều luồng bay
# ─────────────────────────────────────────────────────
else:
    # Vùng nhiễu diện rộng
    z_lat = [3.0, 3.0, 9.5, 9.5, 3.0]
    z_lon = [101.5, 107.5, 107.5, 101.5, 101.5]

    def inject_spoof(true_arr):
        """Tiêm nhiễu giả mạo vào đoạn giữa hành trình."""
        res = true_arr.copy()
        res[35:75] += 0.40 * np.random.normal(size=40)
        return res

    # GNSS bị nhiễu (spoofed) cho cả 3 luồng
    g_lat1, g_lon1 = inject_spoof(t_lat1), inject_spoof(t_lon1)
    g_lat2, g_lon2 = inject_spoof(t_lat2), inject_spoof(t_lon2)
    g_lat3, g_lon3 = inject_spoof(t_lat3), inject_spoof(t_lon3)

    # Resilient Navigation: Bộ lọc hồi phục tọa độ cho cả 3 luồng bay
    r_lat1 = pd.Series(g_lat1).rolling(window=15, center=True, min_periods=1).mean().values.copy()
    r_lon1 = pd.Series(g_lon1).rolling(window=15, center=True, min_periods=1).mean().values.copy()
    r_lat2 = pd.Series(g_lat2).rolling(window=15, center=True, min_periods=1).mean().values.copy()
    r_lon2 = pd.Series(g_lon2).rolling(window=15, center=True, min_periods=1).mean().values.copy()
    r_lat3 = pd.Series(g_lat3).rolling(window=15, center=True, min_periods=1).mean().values.copy()
    r_lon3 = pd.Series(g_lon3).rolling(window=15, center=True, min_periods=1).mean().values.copy()
  
    # 2. SỬA LỖI BIÊN TẠI 0 PHÚT cho cả 3 luồng (Đặt ở đây)
    r_lat1[:35] = t_lat1[:35]
    r_lon1[:35] = t_lon1[:35]
    r_lat2[:35] = t_lat2[:35]
    r_lon2[:35] = t_lon2[:35]
    r_lat3[:35] = t_lat3[:35]
    r_lon3[:35] = t_lon3[:35]
    
    # Giả định sau điểm thứ 85 (hoặc 90 tùy n_points), hệ thống đã phục hồi hoàn toàn
    r_lat1[85:] = t_lat1[85:]
    r_lon1[85:] = t_lon1[85:]
    r_lat2[85:] = t_lat2[85:]
    r_lon2[85:] = t_lon2[85:]
    r_lat3[85:] = t_lat3[85:]
    r_lon3[85:] = t_lon3[85:]


# 1. Tính sai số cho Luồng 1 (SGN -> SIN)
    mean_lat_a1 = (r_lat1 + t_lat1) / 2
    dlat_nm_a1 = (r_lat1 - t_lat1) * 60
    dlon_nm_a1 = (r_lon1 - t_lon1) * 60 * np.cos(np.radians(mean_lat_a1))
    err_flight1 = np.sqrt(dlat_nm_a1**2 + dlon_nm_a1**2)

    # 2. Tính sai số cho Luồng 2 (PNH -> KUL)
    mean_lat_a2 = (r_lat2 + t_lat2) / 2
    dlat_nm_a2 = (r_lat2 - t_lat2) * 60
    dlon_nm_a2 = (r_lon2 - t_lon2) * 60 * np.cos(np.radians(mean_lat_a2))
    err_flight2 = np.sqrt(dlat_nm_a2**2 + dlon_nm_a2**2)

    # 3. Tính sai số cho Luồng 3 (BKK -> CGK)
    mean_lat_a3 = (r_lat3 + t_lat3) / 2
    dlat_nm_a3 = (r_lat3 - t_lat3) * 60
    dlon_nm_a3 = (r_lon3 - t_lon3) * 60 * np.cos(np.radians(mean_lat_a3))
    err_flight3 = np.sqrt(dlat_nm_a3**2 + dlon_nm_a3**2)

    # ĐÃ SỬA: Tính sai số trung bình của toàn bộ không lưu trong vùng ảnh hưởng tại mỗi thời điểm
    error_array = (err_flight1 + err_flight2 + err_flight3) / 3

    # Animation Frames
    for i in range(2, n_points):
        frames.append(go.Frame(data=[
            # FL1
            go.Scattermapbox(lat=t_lat1[:i], lon=t_lon1[:i], mode='lines', line=dict(color='green', width=2)),
            go.Scattermapbox(lat=g_lat1[35:max(36, i)] if i > 35 else [None], lon=g_lon1[35:max(36, i)] if i > 35 else [None], mode='markers', marker=dict(size=4, color='red')),
            go.Scattermapbox(lat=r_lat1[:i], lon=r_lon1[:i], mode='lines', line=dict(color='blue', width=2)),
            # FL2
            go.Scattermapbox(lat=t_lat2[:i], lon=t_lon2[:i], mode='lines', line=dict(color='darkgreen', width=2)),
            go.Scattermapbox(lat=g_lat2[35:max(36, i)] if i > 35 else [None], lon=g_lon2[35:max(36, i)] if i > 35 else [None], mode='markers', marker=dict(size=4, color='magenta')),
            go.Scattermapbox(lat=r_lat2[:i], lon=r_lon2[:i], mode='lines', line=dict(color='dodgerblue', width=2)),
            # FL3
            go.Scattermapbox(lat=t_lat3[:i], lon=t_lon3[:i], mode='lines', line=dict(color='seagreen', width=2)),
            go.Scattermapbox(lat=g_lat3[35:max(36, i)] if i > 35 else [None], lon=g_lon3[35:max(36, i)] if i > 35 else [None], mode='markers', marker=dict(size=4, color='darkorange')),
            go.Scattermapbox(lat=r_lat3[:i], lon=r_lon3[:i], mode='lines', line=dict(color='cyan', width=2)),
            # Vùng nhiễu
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.04)', line=dict(color='red', width=3)),
        ], name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat1[:2], lon=t_lon1[:2], mode='lines', line=dict(color='green', width=2), name='Radar FL1 (TSN→SIN)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='markers', marker=dict(size=4, color='red'), name='Nhiễu GNSS FL1'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat1[:2], lon=r_lon1[:2], mode='lines', line=dict(color='blue', width=2), name='INS/DME FL1 (Resilient)'))
    fig_map.add_trace(go.Scattermapbox(lat=t_lat2[:2], lon=t_lon2[:2], mode='lines', line=dict(color='darkgreen', width=2), name='Radar FL2 (PNH→KUL)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='markers', marker=dict(size=4, color='magenta'), name='Nhiễu GNSS FL2'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat2[:2], lon=r_lon2[:2], mode='lines', line=dict(color='dodgerblue', width=2), name='INS/DME FL2 (Resilient)'))
    fig_map.add_trace(go.Scattermapbox(lat=t_lat3[:2], lon=t_lon3[:2], mode='lines', line=dict(color='seagreen', width=2), name='Radar FL3 (BKK→CGK)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='markers', marker=dict(size=4, color='darkorange'), name='Nhiễu GNSS FL3'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat3[:2], lon=r_lon3[:2], mode='lines', line=dict(color='cyan', width=2), name='INS/DME FL3 (Resilient)'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.04)', line=dict(color='red', width=3), name='Vùng Can Thiệp Diện Rộng'))

    status_text = "🔥 **ATFM Response (Khẩn cấp):** Sự cố nhiễu diện rộng tác động lớn đến nhiều luồng không lưu quốc tế đồng thời. Kích hoạt giải pháp ATFM khẩn cấp..."

# =====================================================
# CẤU HÌNH CHUNG BẢN ĐỒ VÀ NÚT ANIMATION PLAY/PAUSE
# =====================================================
fig_map.frames = frames
fig_map.update_layout(
    mapbox=dict(
        style="open-street-map",
        center=dict(lat=5.5, lon=104.8),
        zoom=4.2
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=680,
    legend=dict(
        yanchor="top", y=0.98, xanchor="left", x=0.02,
        bgcolor="rgba(255, 255, 255, 0.9)",
        font=dict(color="black", size=11),
        bordercolor="gray", borderwidth=1
    ),
    updatemenus=[
        dict(
            type="buttons", direction="left",
            x=0.5, y=-0.05, xanchor="center", yanchor="top",
            buttons=[
                dict(
                    label="▶ Khởi Chạy Mô Phỏng",
                    method="animate",
                    args=[None, {
                        "frame": {"duration": 100, "redraw": True},
                        "transition": {"duration": 0},
                        "fromcurrent": True
                    }]
                ),
                dict(
                    label="⏸ Tạm Dừng",
                    method="animate",
                    args=[[None], {
                        "mode": "immediate",
                        "frame": {"duration": 0, "redraw": False}
                    }]
                )
            ]
        )
    ]
)

# =====================================================
# DỮ LIỆU NỘI DUNG CỘT PHẢI — theo từng kịch bản
# =====================================================

# ── Timeline ứng phó ──────────────────────────────────────────────────
TIMELINE_DATA = {
    "1": [
        ("T+00:00", "#4A90E2", "🔵 Phát hiện",  "RAIM báo mất tín hiệu GNSS tại waypoint BITOD — phân khu M753."),
        ("T+01:45", "#E8A020", "🟠 Cảnh báo",   "ATCO nhận cảnh báo mất PBN. Xác nhận với tổ lái."),
        ("T+03:00", "#D0021B", "🔴 Kích hoạt",  "Chuyển từ GNSS/RNP sang Radar PSR/SSR. Tăng phân cách lên 10 NM."),
        ("T+05:00", "#C8A800", "🟡 Ứng phó",    "Phát NOTAM vùng P-600. INS/DME kích hoạt làm hệ thống dự phòng."),
        ("T+12:00", "#00A550", "🟢 Phục hồi",   "GNSS khôi phục. Kiểm tra RAIM đạt yêu cầu. Trở lại khai thác PBN."),
    ],
    "2": [
        ("T+00:00", "#4A90E2", "🔵 Phát hiện",  "ADS-B báo vị trí VN456 lệch >5 NM so với vết Radar SSR — nghi Spoofing."),
        ("T+00:45", "#D0021B", "🔴 Cảnh báo",   "ATCO đối chiếu Radar vs ADS-B. Xác nhận sai lệch nghiêm trọng."),
        ("T+02:00", "#D0021B", "🔴 Kích hoạt",  "Phát lệnh khẩn: tổ lái cô lập GPS, chuyển sang INS độc lập."),
        ("T+04:00", "#C8A800", "🟡 Phối hợp",   "Phối hợp FIR HCM — Singapore. Tăng phân cách cao lên FL20."),
        ("T+15:00", "#00A550", "🟢 Phục hồi",   "Tàu bay ra khỏi vùng nhiễu. Khôi phục GNSS, xác minh bằng DME/DME."),
    ],
    "3": [
        ("T+00:00", "#4A90E2", "🔵 Phát hiện",  "Nhiều tàu bay mất GNSS đồng thời trên 3 luồng SGN→SIN, PNH→KUL, BKK→CGK."),
        ("T+01:00", "#D0021B", "🔴 Cảnh báo",   "FIR HCM kích hoạt GNSS SIGMET. Thông báo khẩn toàn bộ tàu bay trong vùng."),
        ("T+03:00", "#D0021B", "🔴 ATFM",       "Đình chỉ clearance PBN. Áp dụng phân cách Radar. Giảm năng lực 40%."),
        ("T+06:00", "#E8A020", "🟠 Phối hợp",   "Liên FIR: Singapore, Bangkok, Jakarta. Điều chỉnh CTOT tại sân khởi hành."),
        ("T+10:00", "#C8A800", "🟡 Ổn định",    "NOTAM chính thức. INS/DME dự phòng ổn định trên các luồng ảnh hưởng."),
        ("T+30:00", "#00A550", "🟢 Phục hồi",   "Nguồn nhiễu vô hiệu hóa. Khôi phục dần năng lực PBN theo từng phân khu."),
    ],
}

# ── Bảng so sánh hệ thống ─────────────────────────────────────────────
NAV_TABLE_DATA = {
    "1": [
        ("GNSS / GPS",     "❌",  "Không khả dụng", "#D0021B", "Bị Jamming — RAIM báo lỗi toàn vẹn"),
        ("INS (Quán tính)","✅",  "±0.5 NM",        "#00A550", "Dẫn đường dự phòng chính — drift tăng dần"),
        ("DME/DME",        "✅",  "±0.3 NM",        "#00A550", "Hỗ trợ hiệu chỉnh vị trí cho INS"),
        ("Radar PSR/SSR",  "✅",  "±0.1 NM",        "#00A550", "ATC chuyển sang dẫn dắt Radar mặt đất"),
    ],
    "2": [
        ("GNSS / GPS",     "⚠️", "Lệch >5 NM",     "#E8A020", "Spoofing — tọa độ ADS-B sai lệch nghiêm trọng"),
        ("INS (Quán tính)","✅",  "±0.5 NM",        "#00A550", "Cô lập GPS, chuyển hoàn toàn sang INS"),
        ("DME/DME",        "✅",  "±0.3 NM",        "#00A550", "Cross-check vị trí độc lập với GNSS"),
        ("Radar PSR/SSR",  "✅",  "±0.1 NM",        "#00A550", "Nguồn tham chiếu vị trí tin cậy của ATC"),
    ],
    "3": [
        ("GNSS / GPS",     "❌",  "Không khả dụng", "#D0021B", "Ảnh hưởng đồng thời 3 luồng bay quốc tế"),
        ("INS (Quán tính)","✅",  "±0.8 NM",        "#00A550", "Drift tích lũy cao do thời gian bay dài"),
        ("DME/DME",        "✅",  "±0.3 NM",        "#00A550", "Ưu tiên khai thác tại các vùng có phủ sóng"),
        ("Radar PSR/SSR",  "⚠️", "±0.1 NM",        "#E8A020", "Năng lực Radar hạn chế khi nhiều luồng đồng thời"),
        ("ATFM / CTOT",    "✅",  "—",              "#00A550", "Giảm tải luồng từ sân khởi hành — phối hợp liên FIR"),
    ],
}

# Xác định kịch bản hiện tại
sc_key = "1" if "Kịch bản 1" in scenario else ("2" if "Kịch bản 2" in scenario else "3")
timeline_items = TIMELINE_DATA[sc_key]
nav_rows       = NAV_TABLE_DATA[sc_key]

# =====================================================
# BỐ CỤC HIỂN THỊ CHÍNH: BẢN ĐỒ (trái) + PANEL (phải)
# =====================================================
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown(
        "<p style='font-size:16px;font-weight:700;color:#aac4e0;margin-bottom:4px;'>"
        "🌐 Bản đồ Giám sát và Phân khu Không phận</p>",
        unsafe_allow_html=True
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col2:
    import streamlit.components.v1 as components

    # ── Timeline ứng phó ─────────────────────────────
    timeline_rows_html = ""
    for (time_label, accent_color, phase, desc) in timeline_items:
        timeline_rows_html += (
            f'<div style="display:flex;align-items:flex-start;margin-bottom:7px;gap:10px;'
            f'background:#1e2130;border-radius:7px;padding:8px 11px;'
            f'border-left:4px solid {accent_color};">'
            f'<div style="min-width:60px;font-size:11px;font-weight:700;color:#aac4e0;'
            f'font-family:monospace;padding-top:2px;flex-shrink:0;">{time_label}</div>'
            f'<div>'
            f'<div style="font-weight:800;font-size:13px;color:#ffffff;margin-bottom:2px;">{phase}</div>'
            f'<div style="font-size:11px;color:#ccd8e8;line-height:1.45;">{desc}</div>'
            f'</div>'
            f'</div>'
        )

    # ── Bảng so sánh hệ thống ────────────────────────
    table_rows_html = ""
    for i, (sys_name, icon, accuracy, color, note) in enumerate(nav_rows):
        row_bg = "#1a1f2e" if i % 2 == 0 else "#151929"
        table_rows_html += (
            f'<div style="display:grid;grid-template-columns:1.8fr 0.6fr 1.2fr 2.6fr;gap:5px;'
            f'background:{row_bg};padding:9px 10px;border-radius:6px;'
            f'margin-bottom:4px;border-left:3px solid {color};">'
            f'<div style="font-size:13px;font-weight:700;color:#e8edf5;align-self:center;">{sys_name}</div>'
            f'<div style="font-size:17px;text-align:center;align-self:center;">{icon}</div>'
            f'<div style="font-size:12px;font-weight:600;color:{color};font-family:monospace;align-self:center;">{accuracy}</div>'
            f'<div style="font-size:11px;color:#b0bece;line-height:1.4;align-self:center;">{note}</div>'
            f'</div>'
        )

    # ── Ghép panel: Timeline trên — So sánh dưới ─────
    full_html = (
        '<!DOCTYPE html><html><body style="margin:0;padding:0;background:transparent;">'
        '<div style="height:710px;overflow-y:auto;padding-right:6px;'
        'scrollbar-width:thin;scrollbar-color:#445 #0d1117;font-family:sans-serif;">'

        # TIMELINE
        '<p style="font-size:15px;font-weight:800;color:#ffffff;margin:0 0 8px 0;">'
        '&#128336; Quy tr&igrave;nh &Uacute;ng ph&oacute; S&#7921; c&#7889;</p>'

        + timeline_rows_html

        # Đường kẻ phân cách
        + '<div style="border-top:2px solid #334;margin:12px 0 10px 0;"></div>'

        # BẢNG SO SÁNH
        '<p style="font-size:15px;font-weight:800;color:#ffffff;margin:0 0 7px 0;">'
        '&#128225; So s&aacute;nh H&#7879; th&#7889;ng D&#7851;n &#273;&#432;&#7901;ng</p>'

        '<div style="display:grid;grid-template-columns:1.8fr 0.6fr 1.2fr 2.6fr;gap:5px;'
        'background:#0d1117;padding:7px 10px;border-radius:6px;margin-bottom:5px;">'
        '<div style="font-size:12px;font-weight:800;color:#7eb3d8;">H&#7878; TH&#7888;NG</div>'
        '<div style="font-size:12px;font-weight:800;color:#7eb3d8;text-align:center;">T/T</div>'
        '<div style="font-size:12px;font-weight:800;color:#7eb3d8;">&#272;&#7896; CH&Iacute;NH X&Aacute;C</div>'
        '<div style="font-size:12px;font-weight:800;color:#7eb3d8;">GHI CH&Uacute;</div>'
        '</div>'

        + table_rows_html

        + '</div></body></html>'
    )

    components.html(full_html, height=720, scrolling=False)

# =====================================================
# ADVANCED RESILIENCE ANALYTICS
# =====================================================
st.markdown("---")

max_error = float(np.max(error_array))
mean_error = float(np.mean(error_array))

if sc_key == "1":
    detection_time = "1.75 min"
    recovery_time = "12 min"
    affected_aircraft = 1
    capacity_loss = 10
    severity = "E NO SAFETY EFFECT - ADVISORY"
    sev_color = "orange"
elif sc_key == "2":
    detection_time = "45 sec"
    recovery_time = "15 min"
    affected_aircraft = 1
    capacity_loss = 15
    severity = "C SIGNIFICANT INCIDENT - CRITICAL"
    sev_color = "red"
else:
    detection_time = "1 min"
    recovery_time = "30 min"
    affected_aircraft = 3
    capacity_loss = 40
    severity = "B MAJOR INCIDENT - EMERGENCY"
    sev_color = "darkred"

st.subheader("GNSS Resilience KPI Dashboard")

k1,k2,k3,k4,k5 = st.columns(5)

k1.metric("Max Position Error", f"{max_error:.2f} NM")
k2.metric("Mean Error", f"{mean_error:.2f} NM")
k3.metric("Detection Time", detection_time)
k4.metric("Affected Aircraft", affected_aircraft)
k5.metric("Capacity Reduction", f"-{capacity_loss}%")

#  ĐOẠN CODE MỚI THAY THẾ:
# Quy đổi 100 điểm dữ liệu thành 120 phút bay thực tế
time_axis = np.linspace(0, 120, len(error_array))

fig_error = go.Figure()
fig_error.add_trace(
    go.Scatter(
        x=time_axis,  #  Đã đổi sang trục thời gian tính bằng phút
        y=error_array,
        mode="lines",
        name="Position Error",
        line=dict(width=2.5)
    )
)

fig_error.update_layout(
    title="Position Error vs Time",
    xaxis_title="Time (Minutes)",  #  Đổi nhãn thành Phút
    yaxis_title="Error (NM)",
    height=320,
    xaxis=dict(ticksuffix=" min")  # Hiển thị thêm chữ "min" sau mỗi cột mốc thời gian (ví dụ: 20 min, 40 min)
)
st.plotly_chart(fig_error, use_container_width=True)

st.markdown(
    f'''
    <div style="background:{sev_color};
                color:white;
                padding:15px;
                border-radius:10px;
                text-align:center;
                font-size:24px;
                font-weight:bold;">
        ICAO SEVERITY LEVEL : {severity}
    </div>
    ''',
    unsafe_allow_html=True
)

st.subheader("Airspace Capacity Impact")

normal_capacity = 60
current_capacity = int(normal_capacity * (100 - capacity_loss)/100)

fig_capacity = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=current_capacity,
        title={"text":"Aircraft / Hour"},
        gauge={"axis":{"range":[0, normal_capacity]}}
    )
)

fig_capacity.update_layout(height=320)

st.plotly_chart(fig_capacity, use_container_width=True)

integrity_df = pd.DataFrame({
    "lat":[8.5,6.0,3.5],
    "lon":[105,105,105],
    "integrity":[98,65,92]
})
