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

show_non_resilient = st.sidebar.checkbox(
    "🚫 So sánh: KHÔNG áp dụng Resilient Navigation",
    value=False,
    help=(
        "Mô phỏng quỹ đạo THỰC TẾ của tàu bay nếu KHÔNG có INS/DME/Radar dự phòng "
        "và KHÔNG có bộ lọc FDE/cross-check đa nguồn — tức là tổ lái/autopilot tin tưởng "
        "hoàn toàn vào tín hiệu GNSS bị lỗi."
    ),
)

# =====================================================
# THUẬT TOÁN MÔ PHỎNG: TÀU BAY KHÔNG ÁP DỤNG RESILIENT NAVIGATION
# =====================================================
def mo_phong_khong_resilient(t_lat, t_lon, g_lat, g_lon, mode="jump",
                              start_idx=0, end_idx=None, drift_step_deg=0.0006):
    """
    Mô phỏng quỹ đạo THỰC TẾ mà tàu bay sẽ bay nếu KHÔNG áp dụng Resilient
    Navigation.
    """
    n = len(t_lat)
    if end_idx is None:
        end_idx = n
    na_lat, na_lon = t_lat.copy(), t_lon.copy()

    if mode == "jump":
        na_lat[start_idx:end_idx] = 2 * t_lat[start_idx:end_idx] - g_lat[start_idx:end_idx]
        na_lon[start_idx:end_idx] = 2 * t_lon[start_idx:end_idx] - g_lon[start_idx:end_idx]
        # Sau khi thoát vùng ảnh hưởng, không có gì "kéo" tàu bay trở lại route ngay lập tức
        if end_idx < n:
            offset_lat = na_lat[end_idx - 1] - t_lat[end_idx - 1]
            offset_lon = na_lon[end_idx - 1] - t_lon[end_idx - 1]
            fade = np.linspace(1, 0, min(15, n - end_idx))
            k = len(fade)
            na_lat[end_idx:end_idx + k] = t_lat[end_idx:end_idx + k] + offset_lat * fade
            na_lon[end_idx:end_idx + k] = t_lon[end_idx:end_idx + k] + offset_lon * fade

    elif mode == "freeze":
        # Mô phỏng dead-reckoning thuần túy cộng sai số tích lũy (random walk) khi mất GNSS hoàn toàn
        for k in range(start_idx, end_idx):
            na_lat[k] = na_lat[k-1] + np.random.normal(0, 0.0005)
            na_lon[k] = na_lon[k-1] + np.random.normal(0, 0.0005)

    elif mode == "circle":
        # Máy bay tin hoàn toàn vào GNSS giả. Autopilot sẽ bám theo quỹ đạo hình tròn giả mạo.
        alpha = 0.18
        if start_idx > 0:
            na_lat[start_idx-1] = t_lat[start_idx-1]
            na_lon[start_idx-1] = t_lon[start_idx-1]

        for k in range(start_idx, end_idx):
            na_lat[k] = na_lat[k-1] + alpha * (g_lat[k] - na_lat[k-1])
            na_lon[k] = na_lon[k-1] + alpha * (g_lon[k] - na_lon[k-1])

        # Sau khi thoát vùng spoofing máy bay vẫn còn lệch
        if end_idx < n:
            offset_lat = na_lat[end_idx-1] - t_lat[end_idx-1]
            offset_lon = na_lon[end_idx-1] - t_lon[end_idx-1]
            
            # Tính toán số phần tử còn lại thực tế để không bị tràn mảng
            con_lai = n - end_idx
            so_buoc_fade = min(20, con_lai)
            
            if so_buoc_fade > 0:
                fade = np.linspace(1, 0, so_buoc_fade)
                na_lat[end_idx:end_idx+so_buoc_fade] = t_lat[end_idx:end_idx+so_buoc_fade] + offset_lat * fade
                na_lon[end_idx:end_idx+so_buoc_fade] = t_lon[end_idx:end_idx+so_buoc_fade] + offset_lon * fade

    return na_lat, na_lon


def tinh_sai_so_nm(t_lat, t_lon, x_lat, x_lon):
    """Sai số khoảng cách (NM) giữa quỹ đạo x và quỹ đạo thực t."""
    mean_lat = (x_lat + t_lat) / 2
    dlat_nm = (x_lat - t_lat) * 60
    dlon_nm = (x_lon - t_lon) * 60 * np.cos(np.radians(mean_lat))
    return np.sqrt(dlat_nm ** 2 + dlon_nm ** 2)
# =====================================================
# LOI MO PHONG EKF-GRU CHO RESILIENT NAVIGATION
# =====================================================
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


def _gru_anomaly_score(feature_vec, h_prev):
    """
    GRU surrogate nhe de chay truc tiep trong Streamlit ma khong can file model.
    Input feature_vec = [innovation_nm, innovation_rate_nm, gnss_jump_nm].
    Output score 0..1: cang cao cang nghi GNSS anomaly/spoofing.
    """
    x = np.asarray(feature_vec, dtype=float)
    x = np.clip(x / np.array([8.0, 4.0, 8.0]), 0.0, 6.0)

    wz = np.array([1.15, 0.65, 1.05])
    wr = np.array([0.45, 0.25, 0.40])
    wh = np.array([1.35, 0.95, 1.20])

    z = _sigmoid(np.dot(wz, x) + 0.80 * h_prev - 2.20)
    r = _sigmoid(np.dot(wr, x) + 0.35 * h_prev - 1.10)
    h_candidate = np.tanh(np.dot(wh, x) + 0.65 * r * h_prev - 1.80)
    h = (1.0 - z) * h_prev + z * h_candidate
    score = float(_sigmoid(3.20 * h + 0.85 * x[0] + 0.55 * x[2] - 2.15))
    return score, float(h)


def _ekf_update(x, P, z, H, R):
    y = z - H @ x
    S = H @ P @ H.T + R
    K = P @ H.T @ np.linalg.inv(S)
    x = x + K @ y
    P = (np.eye(len(x)) - K @ H) @ P
    return x, P


def mo_phong_ekf_gru_resilient(
    t_lat,
    t_lon,
    g_lat,
    g_lon,
    gnss_available_mask=None,
    alt_available_mask=None,
    alt_sigma_deg=0.0045,
    gru_threshold=0.58,
):
    """
    Mo phong hybrid EKF-GRU:
    - EKF du doan trang thai [lat, lon, v_lat, v_lon].
    - GNSS measurement duoc kiem tra bang innovation + GRU anomaly score.
    - Khi GNSS bi nghi ngo, EKF loai GNSS va cap nhat bang nguon doc lap gia lap
      nhu DME/Radar/ADS-C voi nhieu do alt_sigma_deg.
    """
    n = len(t_lat)
    if gnss_available_mask is None:
        gnss_available_mask = np.ones(n, dtype=bool)
    if alt_available_mask is None:
        alt_available_mask = np.ones(n, dtype=bool)

    # State: lat, lon, vlat, vlon. Van toc khoi tao tu hai diem dau cua route.
    init_vlat = t_lat[1] - t_lat[0] if n > 1 else 0.0
    init_vlon = t_lon[1] - t_lon[0] if n > 1 else 0.0
    x = np.array([t_lat[0], t_lon[0], init_vlat, init_vlon], dtype=float)
    P = np.diag([1e-5, 1e-5, 1e-6, 1e-6])

    F = np.array([
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    H_pos = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ])

    Q = np.diag([2.0e-7, 2.0e-7, 7.0e-8, 7.0e-8])
    R_gnss = np.diag([8.0e-5, 8.0e-5]) ** 2
    R_alt = np.diag([alt_sigma_deg, alt_sigma_deg]) ** 2

    r_lat = np.zeros(n)
    r_lon = np.zeros(n)
    scores = np.zeros(n)
    trusted_gnss = np.zeros(n, dtype=bool)
    h_gru = 0.0
    prev_innovation_nm = 0.0
    prev_gnss = np.array([g_lat[0], g_lon[0]], dtype=float)

    for k in range(n):
        if k > 0:
            x = F @ x
            P = F @ P @ F.T + Q

        pred_pos = H_pos @ x
        gnss_pos = np.array([g_lat[k], g_lon[k]], dtype=float)
        mean_lat = (pred_pos[0] + gnss_pos[0]) / 2.0
        innovation_nm = float(tinh_sai_so_nm(
            np.array([pred_pos[0]]), np.array([pred_pos[1]]),
            np.array([gnss_pos[0]]), np.array([gnss_pos[1]])
        )[0])
        gnss_jump_nm = float(tinh_sai_so_nm(
            np.array([prev_gnss[0]]), np.array([prev_gnss[1]]),
            np.array([gnss_pos[0]]), np.array([gnss_pos[1]])
        )[0]) if k > 0 else 0.0
        innovation_rate_nm = abs(innovation_nm - prev_innovation_nm)

        score, h_gru = _gru_anomaly_score(
            [innovation_nm, innovation_rate_nm, gnss_jump_nm], h_gru
        )
        scores[k] = score

        if gnss_available_mask[k] and score < gru_threshold and innovation_nm < 5.0:
            x, P = _ekf_update(x, P, gnss_pos, H_pos, R_gnss)
            trusted_gnss[k] = True
        elif alt_available_mask[k]:
            # Nguon doc lap gia lap: DME/Radar/ADS-C quanh vi tri thuc, co nhieu do rieng.
            alt_pos = np.array([
                t_lat[k] + np.random.normal(0.0, alt_sigma_deg),
                t_lon[k] + np.random.normal(0.0, alt_sigma_deg),
            ])
            x, P = _ekf_update(x, P, alt_pos, H_pos, R_alt)

        r_lat[k], r_lon[k] = x[0], x[1]
        prev_innovation_nm = innovation_nm
        prev_gnss = gnss_pos

    error_array = tinh_sai_so_nm(t_lat, t_lon, r_lat, r_lon)
    return r_lat, r_lon, error_array, scores, trusted_gnss

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
        "aircraft":    "3 tàu bay",
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

    # Resilient Navigation: Hybrid EKF-GRU loại GNSS khi bị jamming và cập nhật bằng DME/Radar giả lập
    gnss_mask1 = np.ones(n_points, dtype=bool)
    gnss_mask1[40:70] = False
    alt_mask1 = np.ones(n_points, dtype=bool)
    r_lat1, r_lon1, error_array, anomaly_score1, trusted_gnss1 = mo_phong_ekf_gru_resilient(
        t_lat1, t_lon1, g_lat1, g_lon1,
        gnss_available_mask=gnss_mask1,
        alt_available_mask=alt_mask1,
        alt_sigma_deg=0.0040,
        gru_threshold=0.58,
    )

    # ── KHÔNG áp dụng Resilient Navigation: dead-reckoning vòng hở, không INS/DME ──
    na_lat1, na_lon1 = mo_phong_khong_resilient(
        t_lat1, t_lon1, g_lat1, g_lon1, mode="freeze", start_idx=40, end_idx=70
    )
    non_res_error_array = tinh_sai_so_nm(t_lat1, t_lon1, na_lat1, na_lon1)
    non_res_max_dev = float(np.max(non_res_error_array))

    # Animation Frames
    for i in range(2, n_points):
        _frame_data = [
            go.Scattermapbox(lat=t_lat1[:i], lon=t_lon1[:i], mode='lines', line=dict(color='green', width=3)),
            go.Scattermapbox(lat=g_lat1[:i], lon=g_lon1[:i], mode='markers+lines', marker=dict(size=4, color='orange')),
            go.Scattermapbox(lat=r_lat1[:i], lon=r_lon1[:i], mode='lines', line=dict(color='blue', width=4)),
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,165,0,0.06)', line=dict(color='orange', width=2)),
        ]
        if show_non_resilient:
            _frame_data.append(go.Scattermapbox(lat=na_lat1[:i], lon=na_lon1[:i], mode='lines',
                                                  line=dict(color='#ff003c', width=3)))
        frames.append(go.Frame(data=_frame_data, name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat1[:2], lon=t_lon1[:2], mode='lines', line=dict(color='green', width=3), name='Vết Radar PSR/SSR (Thực tế)'))
    fig_map.add_trace(go.Scattermapbox(lat=g_lat1[:2], lon=g_lon1[:2], mode='markers+lines', marker=dict(size=4, color='orange'), name='Tín hiệu Định vị GNSS (Bị đóng băng)'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat1[:2], lon=r_lon1[:2], mode='lines', line=dict(color='blue', width=4), name='Tích hợp Dự Phòng (INS/DME)'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,165,0,0.06)', line=dict(color='orange', width=2), name='Vùng Nhiễu GNSS Cục Bộ'))
    if show_non_resilient:
        fig_map.add_trace(go.Scattermapbox(lat=na_lat1[:2], lon=na_lon1[:2], mode='lines',
                                            line=dict(color='#ff003c', width=3),
                                            name='⚠️ KHÔNG Resilient Nav (giả lập dead-reckoning)'))
        st.sidebar.error(f"⚠️ Không Resilient Nav: lệch tối đa ≈ {non_res_max_dev:.1f} NM khỏi đường bay thật, không tự hiệu chỉnh.")

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

    # Resilient Navigation: Hybrid EKF-GRU phát hiện spoofing bằng chuỗi innovation
    gnss_mask2 = np.ones(n_points, dtype=bool)
    alt_mask2 = np.ones(n_points, dtype=bool)
    r_lat1, r_lon1, error_array, anomaly_score2, trusted_gnss2 = mo_phong_ekf_gru_resilient(
        t_lat1, t_lon1, g_lat1, g_lon1,
        gnss_available_mask=gnss_mask2,
        alt_available_mask=alt_mask2,
        alt_sigma_deg=0.0035,
        gru_threshold=0.55,
    )

    # ── KHÔNG áp dụng Resilient Navigation: autopilot tự lái theo GNSS giả mạo ──
    na_lat1, na_lon1 = mo_phong_khong_resilient(
        t_lat1, t_lon1, g_lat1, g_lon1, mode="jump", start_idx=40, end_idx=85
    )
    non_res_error_array = tinh_sai_so_nm(t_lat1, t_lon1, na_lat1, na_lon1)
    non_res_max_dev = float(np.max(non_res_error_array))

    # Animation Frames
    for i in range(2, n_points):
        _frame_data = [
            go.Scattermapbox(lat=t_lat1[:i], lon=t_lon1[:i], mode='lines', line=dict(color='green', width=3)),
            go.Scattermapbox(lat=g_lat1[40:max(41, i)] if i > 40 else [None], lon=g_lon1[40:max(41, i)] if i > 40 else [None], mode='markers', marker=dict(size=5, color='red')),
            go.Scattermapbox(lat=r_lat1[:i], lon=r_lon1[:i], mode='lines', line=dict(color='blue', width=4)),
            go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.06)', line=dict(color='red', width=2)),
        ]
        if show_non_resilient:
            _frame_data.append(go.Scattermapbox(lat=na_lat1[:i], lon=na_lon1[:i], mode='lines',
                                                  line=dict(color='#ff003c', width=3)))
        frames.append(go.Frame(data=_frame_data, name=str(i)))

    # Initial traces
    fig_map.add_trace(go.Scattermapbox(lat=t_lat1[:2], lon=t_lon1[:2], mode='lines', line=dict(color='green', width=3), name='Vết Radar PSR/SSR (Thực tế)'))
    fig_map.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode='markers', marker=dict(size=5, color='red'), name='Tọa độ Giả mạo (Spoofing)'))
    fig_map.add_trace(go.Scattermapbox(lat=r_lat1[:2], lon=r_lon1[:2], mode='lines', line=dict(color='blue', width=4), name='Xử lý Kháng nhiễu FDE (INS/DME)'))
    fig_map.add_trace(go.Scattermapbox(lat=z_lat, lon=z_lon, mode='lines', fill='toself', fillcolor='rgba(255,0,0,0.06)', line=dict(color='red', width=2), name='Vùng Tấn Công Giả Mạo'))
    if show_non_resilient:
        fig_map.add_trace(go.Scattermapbox(lat=na_lat1[:2], lon=na_lon1[:2], mode='lines',
                                            line=dict(color='#ff003c', width=3),
                                            name='⚠️ KHÔNG Resilient Nav (autopilot lái theo GNSS giả)'))
        st.sidebar.error(f"⚠️ Không Resilient Nav: tàu bay lệch thực tế tối đa ≈ {non_res_max_dev:.1f} NM khỏi route thật, có nguy cơ xâm nhập vùng cấm/mất phân cách.")

    status_text = "🚨 **ATC Response:** Phát hiện sai lệch lớn giữa vết Radar và báo cáo tọa độ ADS-B của tàu bay. Lập tức phát lệnh yêu cầu tổ lái cô lập máy thu GPS, chuyển sang khai thác INS thủ công."

# ─────────────────────────────────────────────────────
# KỊCH BẢN 3: ATFM — Nhiễu diện rộng, nhiều luồng bay
# ─────────────────────────────────────────────────────
elif "Kịch bản 3" in scenario:
    # Vùng nhiễu diện rộng
    z_lat = [3.0, 3.0, 9.5, 9.5, 3.0]
    z_lon = [101.5, 107.5, 107.5, 101.5, 101.5]

    def inject_spoof_in_red_zone(true_lat, true_lon):
        """Chỉ tiêm nhiễu GNSS tại các điểm nằm trong vùng chữ nhật màu đỏ."""
        g_lat = true_lat.copy()
        g_lon = true_lon.copy()
        lat_min, lat_max = min(z_lat), max(z_lat)
        lon_min, lon_max = min(z_lon), max(z_lon)
        inside_zone = (
            (true_lat >= lat_min) & (true_lat <= lat_max) &
            (true_lon >= lon_min) & (true_lon <= lon_max)
        )
        n_inside = int(np.sum(inside_zone))
        if n_inside > 0:
            g_lat[inside_zone] += 0.40 * np.random.normal(size=n_inside)
            g_lon[inside_zone] += 0.40 * np.random.normal(size=n_inside)
        return g_lat, g_lon, inside_zone

    # GNSS chỉ bị nhiễu khi quỹ đạo đi vào vùng chữ nhật màu đỏ
    g_lat1, g_lon1, zone_mask31 = inject_spoof_in_red_zone(t_lat1, t_lon1)
    g_lat2, g_lon2, zone_mask32 = inject_spoof_in_red_zone(t_lat2, t_lon2)
    g_lat3, g_lon3, zone_mask33 = inject_spoof_in_red_zone(t_lat3, t_lon3)

    # Resilient Navigation: mỗi luồng có một EKF cục bộ, GRU score giám sát anomaly theo thời gian
    gnss_mask3 = np.ones(n_points, dtype=bool)
    alt_mask3 = np.ones(n_points, dtype=bool)
    r_lat1, r_lon1, err_flight1, anomaly_score31, trusted_gnss31 = mo_phong_ekf_gru_resilient(
        t_lat1, t_lon1, g_lat1, g_lon1, gnss_mask3, alt_mask3, alt_sigma_deg=0.0045, gru_threshold=0.55
    )
    r_lat2, r_lon2, err_flight2, anomaly_score32, trusted_gnss32 = mo_phong_ekf_gru_resilient(
        t_lat2, t_lon2, g_lat2, g_lon2, gnss_mask3, alt_mask3, alt_sigma_deg=0.0045, gru_threshold=0.55
    )
    r_lat3, r_lon3, err_flight3, anomaly_score33, trusted_gnss33 = mo_phong_ekf_gru_resilient(
        t_lat3, t_lon3, g_lat3, g_lon3, gnss_mask3, alt_mask3, alt_sigma_deg=0.0045, gru_threshold=0.55
    )

    # Sai số trung bình của toàn bộ không lưu trong vùng ảnh hưởng tại mỗi thời điểm
    error_array = (err_flight1 + err_flight2 + err_flight3) / 3

    # ── KHÔNG áp dụng Resilient Navigation: cả 3 luồng đều tự lái theo GNSS bị nhiễu ──
    na_lat1, na_lon1 = mo_phong_khong_resilient(t_lat1, t_lon1, g_lat1, g_lon1, mode="jump", start_idx=35, end_idx=85)
    na_lat2, na_lon2 = mo_phong_khong_resilient(t_lat2, t_lon2, g_lat2, g_lon2, mode="jump", start_idx=35, end_idx=85)
    na_lat3, na_lon3 = mo_phong_khong_resilient(t_lat3, t_lon3, g_lat3, g_lon3, mode="jump", start_idx=35, end_idx=85)
    non_res_error_array = (
        tinh_sai_so_nm(t_lat1, t_lon1, na_lat1, na_lon1)
        + tinh_sai_so_nm(t_lat2, t_lon2, na_lat2, na_lon2)
        + tinh_sai_so_nm(t_lat3, t_lon3, na_lat3, na_lon3)
    ) / 3
    non_res_max_dev = float(np.max(non_res_error_array))

    # Animation Frames
    for i in range(2, n_points):
        _frame_data = [
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
        ]
        if show_non_resilient:
            _frame_data.append(go.Scattermapbox(lat=na_lat1[:i], lon=na_lon1[:i], mode='lines', line=dict(color='#ff003c', width=2)))
            _frame_data.append(go.Scattermapbox(lat=na_lat2[:i], lon=na_lon2[:i], mode='lines', line=dict(color='#ff7a7a', width=2)))
            _frame_data.append(go.Scattermapbox(lat=na_lat3[:i], lon=na_lon3[:i], mode='lines', line=dict(color='#b30000', width=2)))
        frames.append(go.Frame(data=_frame_data, name=str(i)))

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
    if show_non_resilient:
        fig_map.add_trace(go.Scattermapbox(lat=na_lat1[:2], lon=na_lon1[:2], mode='lines', line=dict(color='#ff003c', width=2), name='⚠️ Không Resilient Nav — FL1'))
        fig_map.add_trace(go.Scattermapbox(lat=na_lat2[:2], lon=na_lon2[:2], mode='lines', line=dict(color='#ff7a7a', width=2), name='⚠️ Không Resilient Nav — FL2'))
        fig_map.add_trace(go.Scattermapbox(lat=na_lat3[:2], lon=na_lon3[:2], mode='lines', line=dict(color='#b30000', width=2), name='⚠️ Không Resilient Nav — FL3'))
        st.sidebar.error(f"⚠️ Không Resilient Nav: sai số trung bình 3 luồng lên tới ≈ {non_res_max_dev:.1f} NM, nguy cơ mất phân cách liên luồng cao.")

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

    # Resilient Navigation: EKF-GRU loại bỏ circle spoofing, dùng nguồn độc lập ADS-C/INS giả lập
    gnss_mask4 = np.ones(n_points, dtype=bool)
    alt_mask4 = np.ones(n_points, dtype=bool)
    r_lat4a, r_lon4a, err_flight4a, anomaly_score4a, trusted_gnss4a = mo_phong_ekf_gru_resilient(
        t_lat4a, t_lon4a, g_lat4a, g_lon4a, gnss_mask4, alt_mask4, alt_sigma_deg=0.0060, gru_threshold=0.52
    )
    r_lat4b, r_lon4b, err_flight4b, anomaly_score4b, trusted_gnss4b = mo_phong_ekf_gru_resilient(
        t_lat4b, t_lon4b, g_lat4b, g_lon4b, gnss_mask4, alt_mask4, alt_sigma_deg=0.0060, gru_threshold=0.52
    )
    r_lat4c, r_lon4c, err_flight4c, anomaly_score4c, trusted_gnss4c = mo_phong_ekf_gru_resilient(
        t_lat4c, t_lon4c, g_lat4c, g_lon4c, gnss_mask4, alt_mask4, alt_sigma_deg=0.0060, gru_threshold=0.52
    )

    # Sai số vị trí (so với quỹ đạo thực) — dùng để dựng KPI và biểu đồ
    def calc_error(t_lat, t_lon, r_lat, r_lon):
        mean_lat = (r_lat + t_lat) / 2
        dlat_nm = (r_lat - t_lat) * 60
        dlon_nm = (r_lon - t_lon) * 60 * np.cos(np.radians(mean_lat))
        return np.sqrt(dlat_nm**2 + dlon_nm**2)
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

    # ── KHÔNG áp dụng Resilient Navigation: autopilot lái theo "vòng tròn" giả mạo ──
    na_lat4a, na_lon4a = mo_phong_khong_resilient(t_lat4a, t_lon4a, g_lat4a, g_lon4a, mode="circle", start_idx=SPOOF_START, end_idx=SPOOF_END)
    na_lat4b, na_lon4b = mo_phong_khong_resilient(t_lat4b, t_lon4b, g_lat4b, g_lon4b, mode="circle", start_idx=SPOOF_START, end_idx=SPOOF_END)
    na_lat4c, na_lon4c = mo_phong_khong_resilient(t_lat4c, t_lon4c, g_lat4c, g_lon4c, mode="circle", start_idx=SPOOF_START, end_idx=SPOOF_END)
    non_res_error_array = (
        calc_error(t_lat4a, t_lon4a, na_lat4a, na_lon4a)
        + calc_error(t_lat4b, t_lon4b, na_lat4b, na_lon4b)
        + calc_error(t_lat4c, t_lon4c, na_lat4c, na_lon4c)
    ) / 3
    non_res_max_dev = float(np.max(non_res_error_array))

    # Animation Frames
    for i in range(2, n_points):
        _frame_data = [
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
        ]
        if show_non_resilient:
            _frame_data.append(go.Scattermapbox(lat=na_lat4a[:i], lon=na_lon4a[:i], mode='lines', line=dict(color='#ff003c', width=2)))
            _frame_data.append(go.Scattermapbox(lat=na_lat4b[:i], lon=na_lon4b[:i], mode='lines', line=dict(color='#ff7a7a', width=2)))
            _frame_data.append(go.Scattermapbox(lat=na_lat4c[:i], lon=na_lon4c[:i], mode='lines', line=dict(color='#b30000', width=2)))
        frames.append(go.Frame(data=_frame_data, name=str(i)))

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
    if show_non_resilient:
        fig_map.add_trace(go.Scattermapbox(lat=na_lat4a[:2], lon=na_lon4a[:2], mode='lines', line=dict(color='#ff003c', width=2), name='⚠️ Không Resilient Nav — FL-A'))
        fig_map.add_trace(go.Scattermapbox(lat=na_lat4b[:2], lon=na_lon4b[:2], mode='lines', line=dict(color='#ff7a7a', width=2), name='⚠️ Không Resilient Nav — FL-B'))
        fig_map.add_trace(go.Scattermapbox(lat=na_lat4c[:2], lon=na_lon4c[:2], mode='lines', line=dict(color='#b30000', width=2), name='⚠️ Không Resilient Nav — FL-C'))
        st.sidebar.error(f"⚠️ Không Resilient Nav: tàu bay thực sự lái theo vòng tròn giả, lệch trung bình ≈ {non_res_max_dev:.1f} NM — nguy cơ va chạm/xâm nhập vùng biển tranh chấp cực cao.")

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
# TOM TAT KPI EKF-GRU
# =====================================================
max_error_nm = float(np.max(error_array)) if "error_array" in globals() else 0.0
mean_error_nm = float(np.mean(error_array)) if "error_array" in globals() else 0.0
st.info(
    f"EKF-GRU Fusion đang hoạt động | Sai số max: {max_error_nm:.2f} NM | "
    f"Sai số TB: {mean_error_nm:.2f} NM | GNSS được kiểm tra bằng innovation + GRU anomaly score"
)
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


# =====================================================
# SIMULATION KPI SUMMARY
# =====================================================
st.subheader("Simulation KPIs")

def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default

def _collect_prefixed_arrays(prefix):
    arrays = []
    for name, value in globals().items():
        if name.startswith(prefix):
            arr = np.asarray(value)
            if arr.ndim == 1 and len(arr) == n_points:
                arrays.append(arr)
    return arrays

ekf_error = np.asarray(error_array) if "error_array" in globals() else np.zeros(n_points)
non_res_error = np.asarray(non_res_error_array) if "non_res_error_array" in globals() else np.zeros(n_points)

anomaly_arrays = _collect_prefixed_arrays("anomaly_score")
if anomaly_arrays:
    anomaly_series = np.mean([arr.astype(float) for arr in anomaly_arrays], axis=0)
else:
    anomaly_series = np.zeros(n_points)

trusted_arrays = _collect_prefixed_arrays("trusted_gnss")
if trusted_arrays:
    trusted_series = np.mean([arr.astype(float) for arr in trusted_arrays], axis=0)
else:
    trusted_series = np.zeros(n_points)

alert_threshold = 0.58
alert_indices = np.where(anomaly_series >= alert_threshold)[0]
time_to_alert_steps = None if len(alert_indices) == 0 else int(alert_indices[0])
gnss_rejected_steps = int(np.sum(trusted_series < 0.5))

nav_kpi_df = pd.DataFrame([
    ("max_error_nm", "Sai số EKF-GRU lớn nhất", f"{np.max(ekf_error):.2f} NM"),
    ("mean_error_nm", "Sai số EKF-GRU trung bình", f"{np.mean(ekf_error):.2f} NM"),
    ("non_res_max_dev", "Độ lệch lớn nhất của phương án không resilient", f"{_safe_float(globals().get('non_res_max_dev')):.2f} NM"),
], columns=["Chỉ số", "Ý nghĩa", "Giá trị"])

ekf_gru_kpi_df = pd.DataFrame([
    ("max anomaly score", "Điểm nghi ngờ GNSS lớn nhất", f"{np.max(anomaly_series):.2f}"),
    ("mean anomaly score", "Điểm nghi ngờ GNSS trung bình", f"{np.mean(anomaly_series):.2f}"),
    ("GNSS trusted rate", "Tỷ lệ GNSS được EKF tin dùng", f"{np.mean(trusted_series) * 100:.1f}%"),
], columns=["Chỉ số", "Ý nghĩa", "Giá trị"])

capacity_kpi_df = pd.DataFrame([
    ("capacity_loss", "Phần trăm suy giảm năng lực vùng trời", f"{capacity_loss}%"),
    ("normal_capacity", "Năng lực bình thường", f"{normal_capacity} aircraft/hour"),
    ("current_capacity", "Năng lực còn lại sau sự cố", f"{current_capacity} aircraft/hour"),
], columns=["Chỉ số", "Ý nghĩa", "Giá trị"])

kpi_tab1, kpi_tab2, kpi_tab3, kpi_tab4 = st.tabs([
    "Sai số dẫn đường",
    "EKF-GRU",
    "Spoofing KB4",
    "Năng lực vùng trời",
])

with kpi_tab1:
    st.dataframe(nav_kpi_df, use_container_width=True, hide_index=True)
    fig_error = go.Figure()
    fig_error.add_trace(go.Scatter(x=list(range(len(ekf_error))), y=ekf_error, mode="lines", name="EKF-GRU error", line=dict(color="#1f77b4", width=2)))
    fig_error.add_trace(go.Scatter(x=list(range(len(non_res_error))), y=non_res_error, mode="lines", name="Không resilient", line=dict(color="#D0021B", width=2)))
    fig_error.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Bước mô phỏng", yaxis_title="Sai số (NM)")
    st.plotly_chart(fig_error, use_container_width=True)

with kpi_tab2:
    st.dataframe(ekf_gru_kpi_df, use_container_width=True, hide_index=True)
    fig_anomaly = go.Figure()
    fig_anomaly.add_trace(go.Scatter(x=list(range(len(anomaly_series))), y=anomaly_series, mode="lines", name="GRU anomaly score", line=dict(color="#E8A020", width=2)))
    fig_anomaly.add_hline(y=alert_threshold, line_dash="dash", line_color="#D0021B", annotation_text="Alert threshold")
    fig_anomaly.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Bước mô phỏng", yaxis_title="Anomaly score", yaxis=dict(range=[0, 1]))
    st.plotly_chart(fig_anomaly, use_container_width=True)

with kpi_tab3:
    if sc_key == "4" and all(name in globals() for name in ["TP", "FN", "FP", "TN", "recall_kb4", "far_kb4", "time_to_alert_min"]):
        spoof_kpi_df = pd.DataFrame([
            ("TP", "Phát hiện đúng spoofing", int(TP)),
            ("FN", "Bỏ sót spoofing", int(FN)),
            ("FP", "Cảnh báo sai", int(FP)),
            ("TN", "Nhận đúng trạng thái bình thường", int(TN)),
            ("recall_kb4", "Tỷ lệ phát hiện đúng", f"{recall_kb4 * 100:.1f}%"),
            ("far_kb4", "Tỷ lệ cảnh báo sai", f"{far_kb4 * 100:.1f}%"),
            ("time_to_alert_min", "Thời gian phát cảnh báo", f"{time_to_alert_min:.1f} phút"),
        ], columns=["Chỉ số", "Ý nghĩa", "Giá trị"])
        st.dataframe(spoof_kpi_df, use_container_width=True, hide_index=True)
    else:
        st.info("Các chỉ số TP/FN/FP/TN chỉ được tính trong Kịch bản 4 - Circle Spoofing.")

with kpi_tab4:
    st.dataframe(capacity_kpi_df, use_container_width=True, hide_index=True)
# Khởi tạo DataFrame mẫu (Giữ lại để tránh lỗi logic nếu các hàm sau có gọi tới)
integrity_df = pd.DataFrame({
    "lat": [8.5, 6.0, 3.5],
    "lon": [105, 105, 105],
    "integrity": [98, 65, 92]
})
