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

st.sidebar.header("📋 Detaylı Kullanıcı Veri Girişi")

# 1. Isınma ve Enerji Modülü
st.sidebar.subheader("1. Isınma ve Enerji")
elektrik_kwh = st.sidebar.number_input(
    "Aylık Elektrik Tüketimi (kWh):", min_value=0, value=250, step=10
)
isinma_turu = st.sidebar.selectbox(
    "Isınma Yakıt Türü:",
    options=["Doğalgaz", "Kömür", "Fındık Kabuğu / Biyokütle", "Odun / Soba"],
)

if isinma_turu == "Kömür":
    Yk = 150
elif isinma_turu == "Doğalgaz":
    Yk = 50
elif isinma_turu == "Odun / Soba":
    Yk = 80
else:
    Yk = 10  # Fındık kabuğu biyokütle

# 2. Tarım ve Ekosistem Modülü (Detaylandırıldı)
st.sidebar.subheader("2. Tarım ve Ekosistem")
bahce_donum = st.sidebar.number_input(
    "Çay / Fındık Bahçesi Alanı (Dönüm):", min_value=0.0, value=5.0, step=0.5
)
gubre_torba = st.sidebar.number_input(
    "Yıllık Kimyasal Gübre Tüketimi (Torba):", min_value=0, value=4, step=1
)
pestisit_kullanimi = st.sidebar.slider(
    "Yıllık Tarımsal İlaçlama Sıklığı (Defa):",
    min_value=0,
    max_value=10,
    value=2,
)

zuruf_yonetimi = st.sidebar.radio(
    "Fındık Zürufu ve Çay Atığı Yönetimi:",
    options=[
        "Bahçede Yakıyorum (Yüksek Emisyon)",
        "Rastgele Bırakıyorum / Kullanmıyorum",
        "Kompost / Doğal Gübre Yapıyorum (Karbon Yutağı)",
    ],
)

if zuruf_yonetimi == "Bahçede Yakıyorum (Yüksek Emisyon)":
    zuruf_skoru = 80
elif zuruf_yonetimi == "Kompost / Doğal Gübre Yapıyorum (Karbon Yutağı)":
    zuruf_skoru = -150  # Makul offset indirimi
else:
    zuruf_skoru = 0

# 3. Ulaşım Modülü
st.sidebar.subheader("3. Ulaşım")
ozel_arac_km = st.sidebar.number_input(
    "Haftalık Özel Araç Mesafesi (km):", min_value=0, value=60, step=10
)
yakit_turu = st.sidebar.selectbox(
    "Yakıt Türü:", options=["Benzin", "Dizel", "LPG / Aracım Yok"]
)
dolmus_sikligi = st.sidebar.slider(
    "Haftalık Dolmuş / Toplu Taşıma Kullanımı (Gün):",
    min_value=0,
    max_value=7,
    value=3,
)

if yakit_turu == "Benzin":
    Fyakit = 0.22
elif yakit_turu == "Dizel":
    Fyakit = 0.28
else:
    Fyakit = 0.08

# 4. Plastik ve Atık Modülü (Detaylandırıldı)
st.sidebar.subheader("4. Plastik ve Atık Yönetimi")
poset_adedi = st.sidebar.number_input(
    "Haftalık Plastik Poşet Tüketimi (Adet):", min_value=0, value=12, step=1
)
sise_ambalaj_adedi = st.sidebar.number_input(
    "Haftalık PET Şişe / Ambalaj Tüketimi (Adet):",
    min_value=0,
    value=10,
    step=1,
)

st.sidebar.markdown("**Geri Dönüşüm Ayrıştırma Alışkanlıkları:**")
cam_ayristirma = st.sidebar.checkbox("Cam Atıkları Ayrıştırıyorum")
kagit_ayristirma = st.sidebar.checkbox("Kağıt / Karton Ayrıştırıyorum")
plastik_ayristirma = st.sidebar.checkbox("Plastik / Metal Ayrıştırıyorum")

# Geri dönüşüm indirim oranı (r)
r = 0.0
if cam_ayristirma:
    r += 0.10
if kagit_ayristirma:
    r += 0.10
if plastik_ayristirma:
    r += 0.15

# ---------------------------------------------------------
# HESAPLAMA VE FORMÜLİZASYON
# ---------------------------------------------------------
I_z = (elektrik_kwh * 0.4) + Yk
T_w = max(
    10,
    (gubre_torba * 35)
    + (pestisit_kullanimi * 15)
    + zuruf_skoru
    - (bahce_donum * 5),
)
U_y = (ozel_arac_km * Fyakit * 4) + (dolmus_sikligi * 2.5)
P_x = ((poset_adedi * 0.15) + (sise_ambalaj_adedi * 0.35)) * (1 - r)

# Yeniden Dengelenmiş Ağırlıklı Ana Fonksiyon
karbon_skoru = (0.35 * I_z) + (0.25 * T_w) + (0.25 * U_y) + (0.15 * P_x)

# ---------------------------------------------------------
# ARAYÜZ VE GÖRSELLEŞTİRME
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.metric(
        label="Hesaplanan Bireysel Karbon Skoru",
        value=f"{round(karbon_skoru, 2)} Puan",
    )

    if karbon_skoru < 65:
        st.success("🟢 **Sınıflandırma:** Düşük Risk (Yeşil)")
    elif 65 <= karbon_skoru <= 130:
        st.warning("🟡 **Sınıflandırma:** Orta Risk (Sarı)")
    else:
        st.error("🔴 **Sınıflandırma:** Kritik Risk (Kırmızı)")

with col2:
    st.subheader("🔍 Modül Bazlı Emisyon Katkı Dağılımı")
    modul_df = pd.DataFrame(
        {
            "Modül": ["Isınma/Enerji", "Tarım/Ekosistem", "Ulaşım", "Plastik/Atık"],
            "Katkı Skoru (Puan)": [
                round(0.35 * I_z, 2),
                round(0.25 * T_w, 2),
                round(0.25 * U_y, 2),
                round(0.15 * P_x, 2),
            ],
        }
    )
    st.bar_chart(modul_df.set_index("Modül"))

st.markdown("---")
st.subheader("💡 Eco-Algoritma Dinamik Karar Destek Senaryoları")

senaryolar = []

if isinma_turu == "Kömür":
    senaryolar.append(
        "🔥 **Isınma Senaryosu:** Yüksek emisyonlu kömür kullanımı tespit edildi. Eynesil'in yerel biyokütle kaynağı olan **fındık kabuğu** kullanımına geçiş yapılması ısınma skorunuzu doğrudan düşürecektir."
    )

if zuruf_yonetimi == "Bahçede Yakıyorum (Yüksek Emisyon)":
    senaryolar.append(
        "⚠️ **Tarım Uyarı Senaryosu:** Fındık zürufunu yakmak atmosfere doğrudan karbondioksit salar. Yakmak yerine **kompostlaştırarak doğal gübre** yaparsanız skorda yüksek miktarda karbon yutağı indirimi kazanırsınız."
    )
elif gubre_torba > 4 and zuruf_yonetimi != "Kompost / Doğal Gübre Yapıyorum (Karbon Yutağı)":
    senaryolar.append(
        "🌱 **Tarım Senaryosu:** Yüksek kimyasal gübre tüketimi saptandı. **Fındık zürufunu kompostlaştırarak** toprakta organik madde oranını artırabilir ve gübre emisyonunu dengeleyebilirsiniz."
    )

if yakit_turu in ["Benzin", "Dizel"] and ozel_arac_km > 50:
    senaryolar.append(
        "🚘 **Ulaşım Senaryosu:** Şahsi araçla fosil yakıt tüketiminiz yüksek. **Eynesil sahil yolu dolmuş hattını** tercih etmek veya araç paylaşımı yapmak ulaşım emisyonunuzu %35 azaltacaktır."
    )

if (poset_adedi + sise_ambalaj_adedi) > 15 and r < 0.20:
    senaryolar.append(
        "♻️ **Plastik/Atık Senaryosu:** Plastik poşet ve ambalaj tüketiminiz yüksek. Cam, kağıt ve plastik atıkları evde ayrı kutularda biriktirerek geri dönüşüme kazandırmak **%35'e varan atık indirimi** sağlayacaktır."
    )

if senaryolar:
    for s in senaryolar:
        st.info(s)
else:
    st.balloons()
    st.success("🎉 Tüketim ve tarım alışkanlıklarınız Eynesil iklim hedefleri ile tam uyumludur.")
