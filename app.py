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
        "Kịch bản 3: Nhiễu vô tuyến diện rộng & Quản lý luồng (ATFM)",
        "Kịch bản 4: Circle Spoofing diện rộng (Tấn công phối hợp - Trường Sa)"
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
        "systems": [
            ("GNSS",  "❌", "#D0021B"),
            ("INS",   "✅", "#00A550"),
            ("DME",   "✅", "#00A550"),
            ("Radar", "⚠️", "#E8A020"),
        ],
    },
    "Kịch bản 4": {
        "aircraft":    "3+ tàu bay",
        "notam":       "CRITICAL",
        "notam_color": "#D0021B",
        "systems": [
            ("GNSS",  "❌", "#D0021B"),
            ("INS",   "✅", "#00A550"),
            ("DME",   "⚠️", "#E8A020"),
            ("Radar", "⚠️", "#E8A020"),
        ],
    },
}

_aw_key = (
    "Kịch bản 1" if "Kịch bản 1" in scenario else
    ("Kịch bản 2" if "Kịch bản 2" in scenario else
     ("Kịch bản 3" if "Kịch bản 3" in scenario else "Kịch bản 4"))
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
    "<div style='background:#0d1117;border-radius:8px;padding:12px 14px; box-sizing: border-box;'>"

    "<p style='font-size:12px;font-weight:800;color:#7eb3d8;margin:0 0 10px 0;"
    "letter-spacing:.6px;'>🔌 SITUATIONAL AWARENESS</p>"

    # --- KHUNG 1: TÀU BAY ẢNH HƯỞNG (Đã đưa ra ngoài Grid và đặt margin-bottom để giãn cách) ---
    "<div style='background:#1e2130;border-radius:6px;padding:8px 10px;margin-bottom:7px; box-sizing: border-box;'>"
    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:3px;'>TÀU BAY ẢNH HƯỞNG</div>"
    f"<div style='font-size:15px;font-weight:800;color:#ffffff;'>{aw['aircraft']}</div>"
    "</div>"

    # --- KHUNG 2: MỨC ĐỘ NOTAM ---
    "<div style='background:#1e2130;border-radius:6px;padding:8px 10px;margin-bottom:9px; box-sizing: border-box;'>"
    "<div style='font-size:10px;color:#7eb3d8;font-weight:700;margin-bottom:4px;'>MỨC ĐỘ NOTAM</div>"
    f"<div style='font-size:14px;font-weight:800;color:{aw['notam_color']};'>⚠ {aw['notam']}</div>"
    "</div>"

    # --- KHUNG 3: TRẠNG THÁI HỆ THỐNG ---
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
    "Kịch bản 4": ("🎯", "#8e0000", "Kịch bản 4 — Circle Spoofing diện rộng (Trường Sa)"),
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

# ── KB4: 3 luồng bay khu vực Nam FIR HCM / vùng tiếp giáp Trường Sa ──
# Luồng A: Vũng Tàu (VVTS) hướng Đông Nam qua Trường Sa
VTA_LAT, VTA_LON = 10.30, 107.10
SPA_LAT, SPA_LON = 7.90,  113.60
t_lat4a = np.linspace(VTA_LAT, SPA_LAT, n_points)
t_lon4a = np.linspace(VTA_LON, SPA_LON, n_points)

# Luồng B: Côn Đảo hướng Đông Nam qua Nam Trường Sa
CDO_LAT, CDO_LON = 8.70, 106.60
SPB_LAT, SPB_LON = 6.30, 114.10
t_lat4b = np.linspace(CDO_LAT, SPB_LAT, n_points)
t_lon4b = np.linspace(CDO_LON, SPB_LON, n_points)

# Luồng C: Phú Quý hướng Đông qua giữa Trường Sa
PQY_LAT, PQY_LON = 10.90, 108.90
SPC_LAT, SPC_LON = 8.90,  112.50
t_lat4c = np.linspace(PQY_LAT, SPC_LAT, n_points)
t_lon4c = np.linspace(PQY_LON, SPC_LON, n_points)

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
elif "Kịch bản 3" in scenario:
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

# ─────────────────────────────────────────────────────
# KỊCH BẢN 4: CIRCLE SPOOFING DIỆN RỘNG — Tấn công phối hợp
# (Nam FIR HCM / vùng tiếp giáp Trường Sa)
# ─────────────────────────────────────────────────────
else:
    # Vùng tấn công phối hợp — Nam FIR HCM / tiếp giáp Trường Sa
    z_lat = [5.8, 5.8, 10.8, 10.8, 5.8]
    z_lon = [110.0, 116.5, 116.5, 110.0, 110.0]

    SPOOF_START, SPOOF_END = 30, 82  # đoạn hành trình bị "circle spoofing"

    def inject_circle_spoof(t_lat, t_lon, n_loops=2.2, radius_deg=0.28):
        """Giả mạo tọa độ GNSS theo dạng đường tròn (vòng lặp) quanh 1 tâm cố định —
        dấu hiệu đặc trưng của tấn công Circle/Orbit Spoofing phối hợp."""
        g_lat, g_lon = t_lat.copy(), t_lon.copy()
        seg_len = SPOOF_END - SPOOF_START
        center_lat = t_lat[(SPOOF_START + SPOOF_END) // 2]
        center_lon = t_lon[(SPOOF_START + SPOOF_END) // 2]
        angles = np.linspace(0, n_loops * 2 * np.pi, seg_len)
        g_lat[SPOOF_START:SPOOF_END] = center_lat + radius_deg * np.sin(angles)
        g_lon[SPOOF_START:SPOOF_END] = center_lon + radius_deg * np.cos(angles) * 0.9
        return g_lat, g_lon

    # GNSS bị "circle spoofing" đồng thời trên cả 3 luồng
    g_lat4a, g_lon4a = inject_circle_spoof(t_lat4a, t_lon4a)
    g_lat4b, g_lon4b = inject_circle_spoof(t_lat4b, t_lon4b)
    g_lat4c, g_lon4c = inject_circle_spoof(t_lat4c, t_lon4c)

    # Resilient Navigation: đối chiếu chéo đa nguồn (multilateration/ADS-C + INS)
    # phát hiện hình học "đường tròn" bất khả thi -> loại bỏ và khôi phục quỹ đạo thực
    def resilient_recover(t_arr, g_arr):
        r_arr = pd.Series(g_arr).rolling(window=9, center=True, min_periods=1).mean().values.copy()
        r_arr[:SPOOF_START + 5] = t_arr[:SPOOF_START + 5]
        r_arr[SPOOF_END - 5:] = t_arr[SPOOF_END - 5:]
        return r_arr

    r_lat4a = resilient_recover(t_lat4a, g_lat4a)
    r_lon4a = resilient_recover(t_lon4a, g_lon4a)
    r_lat4b = resilient_recover(t_lat4b, g_lat4b)
    r_lon4b = resilient_recover(t_lon4b, g_lon4b)
    r_lat4c = resilient_recover(t_lat4c, g_lat4c)
    r_lon4c = resilient_recover(t_lon4c, g_lon4c)

    # Sai số vị trí (so với quỹ đạo thực) — dùng để dựng KPI và biểu đồ
    def calc_error(t_lat, t_lon, r_lat, r_lon):
        mean_lat = (r_lat + t_lat) / 2
        dlat_nm = (r_lat - t_lat) * 60
        dlon_nm = (r_lon - t_lon) * 60 * np.cos(np.radians(mean_lat))
        return np.sqrt(dlat_nm**2 + dlon_nm**2)

    err_flight4a = calc_error(t_lat4a, t_lon4a, r_lat4a, r_lon4a)
    err_flight4b = calc_error(t_lat4b, t_lon4b, r_lat4b, r_lon4b)
    err_flight4c = calc_error(t_lat4c, t_lon4c, r_lat4c, r_lon4c)
    error_array = (err_flight4a + err_flight4b + err_flight4c) / 3

    # Sai số "thô" của GNSS bị spoof (dùng để mô phỏng bộ phát hiện Recall/FAR)
    raw_err4a = calc_error(t_lat4a, t_lon4a, g_lat4a, g_lon4a)
    raw_err4b = calc_error(t_lat4b, t_lon4b, g_lat4b, g_lon4b)
    raw_err4c = calc_error(t_lat4c, t_lon4c, g_lat4c, g_lon4c)
    raw_error_avg = (raw_err4a + raw_err4b + raw_err4c) / 3

    # ── Mô phỏng bộ phát hiện Circle Spoofing: Recall / False Alarm Rate ──
    DETECT_THRESHOLD_NM = 3.0
    spoof_truth_mask = np.zeros(n_points, dtype=bool)
    spoof_truth_mask[SPOOF_START:SPOOF_END] = True
    detected_mask = raw_error_avg > DETECT_THRESHOLD_NM

    TP = int(np.sum(detected_mask & spoof_truth_mask))
    FN = int(np.sum(~detected_mask & spoof_truth_mask))
    FP = int(np.sum(detected_mask & ~spoof_truth_mask))
    TN = int(np.sum(~detected_mask & ~spoof_truth_mask))

    recall_kb4 = (TP / (TP + FN)) if (TP + FN) > 0 else 0.0
    far_kb4 = (FP / (FP + TN)) if (FP + TN) > 0 else 0.0

    _detect_idx = np.argmax(detected_mask[SPOOF_START:]) + SPOOF_START if np.any(detected_mask[SPOOF_START:]) else SPOOF_END
    time_to_alert_min = (_detect_idx - SPOOF_START) / n_points * 120  # quy đổi ra phút bay

    # Animation Frames
    for i in range(2, n_points):
        frames.append(go.Frame(data=[
            # Luồng A
            go.Scattermapbox(lat=t_lat4a[:i], lon=t_lon4a[:i], mode='lines', line=dict(color='green', width=2)),
            go.Scattermapbox(lat=g_lat4a[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              lon=g_lon4a[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              mode='lines+markers', marker=dict(size=3, color='red'), line=dict(color='red', width=1.5)),
            go.Scattermapbox(lat=r_lat4a[:i], lon=r_lon4a[:i], mode='lines', line=dict(color='blue', width=2)),
            # Luồng B
            go.Scattermapbox(lat=t_lat4b[:i], lon=t_lon4b[:i], mode='lines', line=dict(color='darkgreen', width=2)),
            go.Scattermapbox(lat=g_lat4b[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              lon=g_lon4b[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              mode='lines+markers', marker=dict(size=3, color='magenta'), line=dict(color='magenta', width=1.5)),
            go.Scattermapbox(lat=r_lat4b[:i], lon=r_lon4b[:i], mode='lines', line=dict(color='dodgerblue', width=2)),
            # Luồng C
            go.Scattermapbox(lat=t_lat4c[:i], lon=t_lon4c[:i], mode='lines', line=dict(color='seagreen', width=2)),
            go.Scattermapbox(lat=g_lat4c[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              lon=g_lon4c[SPOOF_START:max(SPOOF_START + 1, i)] if i > SPOOF_START else [None],
                              mode='lines+markers', marker=dict(size=3, color='darkorange'), line=dict(color='darkorange', width=1.5)),
            go.Scattermapbox(lat=r_lat4c[:i], lon=r_lon4c[:i], mode='lines', line=dict(color='cyan', width=2)),
            # Vùng tấn công
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(139,0,0,0.06)', line=dict(color='#8e0000', width=3)),
        ], name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat4a[:2], lon=t_lon4a[:2], mode='lines', line=dict(color='green', width=2), name='Radar FL-A (VVTS→Trường Sa)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='lines+markers', marker=dict(size=3, color='red'), line=dict(color='red', width=1.5), name='Circle Spoofing FL-A'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat4a[:2], lon=r_lon4a[:2], mode='lines', line=dict(color='blue', width=2), name='Khôi phục (Multilateration) FL-A'))
    fig_map.add_trace(go.Scattermapbox(lat=t_lat4b[:2], lon=t_lon4b[:2], mode='lines', line=dict(color='darkgreen', width=2), name='Radar FL-B (Côn Đảo→Nam Trường Sa)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='lines+markers', marker=dict(size=3, color='magenta'), line=dict(color='magenta', width=1.5), name='Circle Spoofing FL-B'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat4b[:2], lon=r_lon4b[:2], mode='lines', line=dict(color='dodgerblue', width=2), name='Khôi phục (Multilateration) FL-B'))
    fig_map.add_trace(go.Scattermapbox(lat=t_lat4c[:2], lon=t_lon4c[:2], mode='lines', line=dict(color='seagreen', width=2), name='Radar FL-C (Phú Quý→Giữa Trường Sa)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='lines+markers', marker=dict(size=3, color='darkorange'), line=dict(color='darkorange', width=1.5), name='Circle Spoofing FL-C'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat4c[:2], lon=r_lon4c[:2], mode='lines', line=dict(color='cyan', width=2), name='Khôi phục (Multilateration) FL-C'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(139,0,0,0.06)', line=dict(color='#8e0000', width=3), name='Vùng Tấn Công Circle Spoofing'))

    status_text = "🎯 **ATC Response (Cấp 3 — Nghiêm trọng nhất):** Phát hiện nhiều tàu bay báo cáo GNSS di chuyển theo quỹ đạo hình tròn bất khả thi (dấu hiệu Circle Spoofing phối hợp) tại khu vực Nam FIR HCM/Trường Sa. Kích hoạt quy trình đối chiếu đa nguồn (ADS-C, multilateration, INS) và cảnh báo khẩn toàn vùng."

# =====================================================
# CẤU HÌNH CHUNG BẢN ĐỒ VÀ NÚT ANIMATION PLAY/PAUSE
# =====================================================
fig_map.frames = frames

# Trung tâm/zoom bản đồ thích ứng theo từng kịch bản
if "Kịch bản 4" in scenario:
    _map_center = dict(lat=8.3, lon=111.5)
    _map_zoom = 5.2
else:
    _map_center = dict(lat=5.5, lon=104.8)
    _map_zoom = 4.2

fig_map.update_layout(
    mapbox=dict(
        style="open-street-map",
        center=_map_center,
        zoom=_map_zoom
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
        ("T+00:00", "#4A90E2", "🔵 Sự cố",      "Tàu bay đi vào khu vực nhiễu GNSS."),
        ("T+00:45", "#E8A020", "🟠 Cảnh báo",   "RAIM cảnh báo mất tính toàn vẹn tín hiệu GNSS. Tổ lái báo cáo ATC về sự cố"),
        ("T+03:00", "#D0021B", "🔴 Ứng phó",    "ATCO xác nhận sự cố, chuyển sang giám sát bằng Radar PSR/SSR và áp dụng phân cách Radar."),
        ("T+10:00", "#C8A800", "🟡 Điều hành",  "Phát hành NOTAM cảnh báo nhiễu GNSS, khuyến cáo sử dụng INS/DME dự phòng."),
        ("T+12:00", "#00A550", "🟢 Phục hồi",   "Nhiễu được loại bỏ. GNSS khôi phục. Trở lại khai thác PBN."),
    ],
    "2": [
        ("T+00:00", "#4A90E2", "🔵 Sự cố",      "Tín hiệu GNSS giả mạo xuất hiện, vị trí GNSS sai lệch khỏi quỹ đạo thực tế."),
        ("T+01:00", "#D0021B", "🔴 Phát hiện",  "ATCO phát hiện sai lệch giữa ADS-B, Radar SSR và dữ liệu dẫn đường."),
        ("T+03:00", "#D0021B", "🔴 Xác nhận",   "Nghi ngờ hiện tượng Spoofing và yêu cầu tố lái thực hiện đối chiếu vị trí bằng INS."),
        ("T+05:00", "#C8A800", "🟡 Ứng phó",    "Theo dõi tàu bay và duy trì phân cách an toàn, tàu bay chuyển sang khai thác INS/DME."),
        ("T+15:00", "#00A550", "🟢 Phục hồi",   "Tàu bay ra khỏi vùng nhiễu. Khôi phục GNSS, khai thác bình thường."),
    ],
    "3": [
        ("T+00:00", "#4A90E2", "🔵 Sự cố",      "Nhiều tàu bay mất GNSS đồng thời trên 3 luồng SGN→SIN, PNH→KUL, BKK→CGK."),
        ("T+03:00", "#D0021B", "🔴 Phát hiện",  "ACC HCM nhận báo cáo mất hoặc suy giảm tín hiệu GNSS từ tàu bay. Đánh giá sự cố."),
        ("T+05:00", "#D0021B", "🔴 ATFM",       "Kích hoạt ATFM, tăng phân cách và hạn chế khai thác các phương thức PBN."),
        ("T+10:00", "#E8A020", "🟠 Phối hợp",   "Phát hành SIGMET và NOTAM, phối hợp với các FIR Singapore, Bangkok và Jakarta."),
        ("T+15:00", "#C8A800", "🟡 Ổn định",    "Duy trì dẫn đường bằng INS/DME và Radar. Luồng được kiểm soát ổn định ở mức giảm tải."),
        ("T+30:00", "#00A550", "🟢 Phục hồi",   "Nguồn nhiễu vô hiệu hóa. Hoạt động dẫn đường GNSS và năng lực khai thác vùng trời được khôi phục."),
    ],
    "4": [
        ("T+00:00", "#4A90E2", "🔵 Sự cố",      "3 tàu bay đồng thời báo cáo tọa độ GNSS di chuyển thành vòng tròn tại Nam FIR HCM/Trường Sa."),
        ("T+02:00", "#D0021B", "🔴 Phát hiện",  "Hệ thống đối chiếu đa nguồn (ADS-C/Multilateration) nhận diện hình học tròn bất khả thi — nghi Circle Spoofing phối hợp."),
        ("T+03:30", "#8e0000", "⚫ Xác nhận Cấp 3", "ACC HCM xác nhận tấn công phối hợp diện rộng, kích hoạt quy trình ứng phó nghiêm trọng nhất (Cấp 3)."),
        ("T+05:00", "#D0021B", "🔴 Cảnh báo",   "Phát SIGMET/NOTAM khẩn, yêu cầu toàn bộ tàu bay trong vùng chuyển sang INS và báo cáo vị trí bằng thoại."),
        ("T+08:00", "#E8A020", "🟠 Phối hợp",   "Phối hợp liên FIR (Singapore, Manila) và cơ quan chức năng xác định nguồn phát spoofing khu vực Trường Sa."),
        ("T+15:00", "#C8A800", "🟡 Kiểm soát",  "Tăng phân cách, áp dụng thủ tục dự phòng phi-GNSS, giám sát chặt các luồng bay lân cận."),
        ("T+35:00", "#00A550", "🟢 Phục hồi",   "Nguồn spoofing bị vô hiệu hóa/tàu bay thoát vùng ảnh hưởng. Khôi phục khai thác GNSS bình thường."),
    ],
}

# ── Bảng so sánh hệ thống ─────────────────────────────────────────────
NAV_TABLE_DATA = {
    "1": [
        ("GNSS / GPS",     "❌",  "Không khả dụng", "#D0021B", "Bị Jamming — RAIM báo lỗi toàn vẹn"),
        ("INS (Quán tính)","✅",  "±0.5-2 NM",      "#00A550", "Dẫn đường dự phòng chính — drift tăng dần"),
        ("DME/DME",        "✅",  "±0.2-0.5 NM",    "#00A550", "Hỗ trợ hiệu chỉnh vị trí cho INS"),
        ("Radar PSR/SSR",  "✅",  "±0.3 NM",        "#00A550", "ATC chuyển sang dẫn dắt Radar mặt đất"),
    ],
    "2": [
        ("GNSS / GPS",     "⚠️", "Lệch >5 NM",     "#E8A020", "Spoofing — tọa độ ADS-B sai lệch nghiêm trọng"),
        ("INS (Quán tính)","✅",  "±0.5 NM",        "#00A550", "Cô lập GPS, chuyển hoàn toàn sang INS"),
        ("DME/DME",        "✅",  "±0.3 NM",        "#00A550", "Cross-check vị trí độc lập với GNSS"),
        ("Radar PSR/SSR",  "✅",  "±0.3 NM",        "#00A550", "Nguồn tham chiếu vị trí tin cậy của ATC"),
    ],
    "3": [
        ("GNSS / GPS",     "❌",  "Không khả dụng", "#D0021B", "Ảnh hưởng đồng thời 3 luồng bay quốc tế"),
        ("INS (Quán tính)","✅",  "±0.8-2 NM",      "#00A550", "Drift tích lũy cao do thời gian bay dài"),
        ("DME/DME",        "✅",  "±0.3 NM",        "#00A550", "Ưu tiên khai thác tại các vùng có phủ sóng"),
        ("Radar PSR/SSR",  "⚠️", "±0.1 NM",         "#E8A020", "Năng lực Radar hạn chế khi nhiều luồng đồng thời"),
        ("ATFM / CTOT",    "✅",  "—",              "#00A550", "Giảm tải luồng từ sân khởi hành — phối hợp liên FIR"),
    ],
    "4": [
        ("GNSS / GPS",         "❌",  "Vòng tròn giả",   "#D0021B", "Circle Spoofing — quỹ đạo GNSS khép vòng bất khả thi"),
        ("ADS-C / Multilateration", "✅", "±0.5-1 NM",  "#00A550", "Đối chiếu chéo đa nguồn để nhận diện dấu hiệu spoof"),
        ("INS (Quán tính)",    "✅",  "±1-2.5 NM",      "#00A550", "Chuyển hoàn toàn sang dẫn đường quán tính khi nghi ngờ"),
        ("DME/DME",             "⚠️", "Hạn chế phủ sóng","#E8A020", "Vùng biển xa — DME/Radar sơ cấp gần như không phủ"),
        ("Radar PSR/SSR",      "⚠️", "Không phủ (oceanic)","#E8A020", "Không có radar sơ cấp — phụ thuộc ADS-B/ADS-C"),
        ("Phối hợp liên FIR",  "✅",  "—",              "#00A550", "Cảnh báo khẩn cấp Cấp 3 tới các FIR lân cận (SIN, Manila)"),
    ],
}

# Xác định kịch bản hiện tại
sc_key = (
    "1" if "Kịch bản 1" in scenario else
    ("2" if "Kịch bản 2" in scenario else
     ("3" if "Kịch bản 3" in scenario else "4"))
)
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
# AIRSPACE CAPACITY IMPACT & CAPACITY LOSS (HIỂN THỊ SONG SONG)
# =====================================================
st.subheader("Airspace Capacity Analysis")

# 1. Định nghĩa mức giảm năng lực thông lượng (capacity_loss) theo từng kịch bản
sc_key = (
    "1" if "Kịch bản 1" in scenario else
    ("2" if "Kịch bản 2" in scenario else
     ("3" if "Kịch bản 3" in scenario else "4"))
)

if sc_key == "1":
    capacity_loss = 10
elif sc_key == "2":
    capacity_loss = 20
elif sc_key == "3":
    capacity_loss = 40
else:  # Kịch bản 4
    capacity_loss = 50

# Tính toán năng lực thông lượng hiện tại dựa trên capacity_loss
normal_capacity = 60
current_capacity = int(normal_capacity * (100 - capacity_loss) / 100)

# 2. CHIA THÀNH 2 CỘT SONG SONG (Cột 1 chiếm tỷ lệ 1, Cột 2 chiếm tỷ lệ 2)
col_loss, col_gauge = st.columns([1, 2])

with col_loss:
    st.markdown("<br><br>", unsafe_allow_html=True) # Tạo khoảng trống nhỏ để căn giữa theo chiều dọc
    st.metric(
        label="📉 Airspace Capacity Loss", 
        value=f"-{capacity_loss}%",
        delta="Hạn chế khai thác",
        delta_color="inverse"
    )
    st.markdown(
        f"<div style='background:#1e2130; padding:12px; border-radius:6px; border-left:4px solid #D0021B;'>"
        f"<span style='font-size:12px; color:#aac4e0;'><b>Trạng thái:</b> Vùng trời bị giảm năng lực cấu trúc do nhiễu tín hiệu dẫn đường. Chuyển đổi phương thức phân cách dòng.</span>"
        f"</div>", 
        unsafe_allow_html=True
    )

with col_gauge:
    # Dựng biểu đồ đồng hồ đo (Gauge Chart) hiển thị dung lượng vùng trời
    fig_capacity = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=current_capacity,
            title={"text": "Current Airspace Capacity (Aircraft / Hour)", "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, normal_capacity]},
                "bar": {"color": "#D0021B" if capacity_loss >= 40 else "#E8A020"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(208, 2, 27, 0.1)"},
                    {"range": [30, 50], "color": "rgba(232, 160, 32, 0.1)"},
                    {"range": [50, 60], "color": "rgba(0, 165, 80, 0.1)"}
                ]
            }
        )
    )
    fig_capacity.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig_capacity, use_container_width=True)

# Khởi tạo DataFrame mẫu (Giữ lại để tránh lỗi logic nếu các hàm sau có gọi tới)
integrity_df = pd.DataFrame({
    "lat": [8.5, 6.0, 3.5],
    "lon": [105, 105, 105],
    "integrity": [98, 65, 92]
})
