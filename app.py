import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Eco-Algoritma | Eynesil Karar Destek Sistemi",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Eco-Algoritma: Eynesil Karar Destek Sistemi")
st.subheader("Yerel Emisyon Optimizasyonu ve Risk Sınıflandırması")
st.markdown("---")

st.sidebar.header("📋 Kullanıcı Veri Girişi")

# 1. Isınma ve Enerji
st.sidebar.subheader("1. Isınma ve Enerji")
elektrik_kwh = st.sidebar.number_input(
    "Aylık Elektrik Tüketimi (kWh):", min_value=0, value=250, step=10
)
isinma_turu = st.sidebar.selectbox(
    "Isınma Yakıt Türü:",
    options=["Doğalgaz", "Kömür", "Fındık Kabuğu / Biyokütle"],
)

if isinma_turu == "Kömür":
    Yk = 150
elif isinma_turu == "Doğalgaz":
    Yk = 50
else:
    Yk = 0

# 2. Tarım ve Ekosistem
st.sidebar.subheader("2. Tarım ve Ekosistem")
gubre_torba = st.sidebar.number_input(
    "Yıllık Kimyasal Gübre Tüketimi (Torba):", min_value=0, value=4, step=1
)
zuruf_kullanimi = st.sidebar.checkbox(
    "Fındık zürufunu doğal gübre/kompost olarak değerlendiriyor musunuz?",
    value=True,
)

Zfindik = 1 if zuruf_kullanimi else 0

# 3. Ulaşım
st.sidebar.subheader("3. Ulaşım")
ozel_arac_km = st.sidebar.number_input(
    "Haftalık Özel Araç Mesafesi (km):", min_value=0, value=50, step=10
)
yakit_turu = st.sidebar.selectbox(
    "Yakıt Türü:", options=["Benzin", "Dizel", "LPG / Yok"]
)
dolmus_sikligi = st.sidebar.slider(
    "Haftalık Dolmuş Kullanım Sıklığı (Gün):",
    min_value=0,
    max_value=7,
    value=2,
)

if yakit_turu == "Benzin":
    Fyakit = 0.19
elif yakit_turu == "Dizel":
    Fyakit = 0.27
else:
    Fyakit = 0.10

# 4. Plastik ve Atık
st.sidebar.subheader("4. Plastik ve Atık")
poset_adedi = st.sidebar.number_input(
    "Haftalık Plastik Poşet Tüketimi (Adet):", min_value=0, value=8, step=1
)
geridonosum = st.sidebar.checkbox(
    "Evsel atıkları (cam/kağıt/plastik) ayrıştırıyor musunuz?", value=False
)

r = 0.20 if geridonosum else 0.0

# Formül
I_z = (elektrik_kwh * 0.4) + Yk
T_w = (gubre_torba * 50) - (Zfindik * 500)
U_y = (ozel_arac_km * Fyakit) + (dolmus_sikligi * 1.5)
P_x = (poset_adedi * 0.05) * (1 - r)

karbon_skoru = (0.40 * I_z) + (0.30 * T_w) + (0.20 * U_y) + (0.10 * P_x)

# Görselleştirme
col1, col2 = st.columns([1, 2])

with col1:
    st.metric(
        label="Hesaplanan Bireysel Karbon Skoru",
        value=f"{round(karbon_skoru, 2)} Puan",
    )

    if karbon_skoru < 50:
        st.success("🟢 **Sınıflandırma:** Düşük Risk (Yeşil)")
    elif 50 <= karbon_skoru <= 120:
        st.warning("🟡 **Sınıflandırma:** Orta Risk (Sarı)")
    else:
        st.error("🔴 **Sınıflandırma:** Kritik Risk (Kırmızı)")

with col2:
    st.subheader("🔍 Modül Bazlı Karbon Dağılımı")
    modul_df = pd.DataFrame(
        {
            "Modül": ["Isınma/Enerji", "Tarım/Ekosistem", "Ulaşım", "Plastik/Atık"],
            "Katkı Skoru": [
                0.40 * I_z,
                max(0, 0.30 * T_w),
                0.20 * U_y,
                0.10 * P_x,
            ],
        }
    )
    st.bar_chart(modul_df.set_index("Modül"))

st.markdown("---")
st.subheader("💡 Eco-Algoritma Dinamik Karar Destek Senaryoları")

senaryolar = []

if isinma_turu == "Kömür":
    senaryolar.append(
        "🔥 **Isınma Senaryosu:** Yüksek emisyonlu kömür kullanımı tespit edildi. Eynesil'in yerel biyokütle kaynağı olan **fındık kabuğu** kullanımına geçiş yapılması durumında ısınma katsayınız karbon-nötr seviyesine yaklaşacaktır."
    )

if gubre_torba > 3 and not zuruf_kullanimi:
    senaryolar.append(
        "🌱 **Tarım Senaryosu:** Yüksek gübre tüketimi saptandı. Atık **fındık zürufunu doğal gübre** olarak değerlendirerek -500 birimlik karbon yutağı indirimi kazanabilirsiniz."
    )

if yakit_turu in ["Benzin", "Dizel"] and ozel_arac_km > 40:
    senaryolar.append(
        "🚘 **Ulaşım Senaryosu:** Fosil yakıtlı araç kullanımınız yüksek. **Eynesil sahil yolu dolmuş hattını** tercih etmek ulaşım emisyonunuzu düşürecektir."
    )

if not geridonosum:
    senaryolar.append(
        "♻️ **Atık Senaryosu:** Atık ayrıştırması yaparak %20 indirim katsayısı (r = 0.20) kazanabilirsiniz."
    )

if senaryolar:
    for s in senaryolar:
        st.info(s)
else:
    st.balloons()
    st.success("🎉 Tüketim alışkanlıklarınız sürdürülebilir seviyededir.")
