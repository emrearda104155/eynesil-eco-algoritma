import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Eco-Algoritma | Eynesil Karar Destek Sistemi",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Eco-Algoritma: Eynesil Karar Destek Sistemi")
st.subheader("17 Parametreli Yerel Emisyon Optimizasyonu ve Risk Sınıflandırması")
st.markdown("---")

st.sidebar.header("📋 Anket Veri Giriş Paneli")

# 1. DEMOGRAFİK BİLGİLER (Soru 1, 2, 3)
st.sidebar.subheader("👤 Demografik Bilgiler")
yas_araligi = st.sidebar.selectbox(
    "1. Yaş Aralığı:",
    ["15 yaşından küçük", "15-25", "26-40", "41-60", "60+"],
    index=2,
)
hane_halki = st.sidebar.number_input(
    "2. Hane Halkı Sayısı (Kişi):", min_value=1, value=4, step=1
)
meslek = st.sidebar.selectbox(
    "3. Temel Geçim Kaynağı / Meslek:",
    ["Memur/İşçi", "Esnaf", "Çay/Fındık Tarımı", "Balıkçılık", "Diğer"],
)

# 2. PLASTİK VE ATIK (Soru 4, 5, 6)
st.sidebar.subheader("♻️ Plastik ve Atık Yönetimi")
poset_adedi = st.sidebar.number_input(
    "4. Haftalık Yeni Plastik Poşet Tüketimi (Adet):",
    min_value=0,
    value=8,
    step=1,
)
tekrar_kullanim = st.sidebar.selectbox(
    "5. Poşetleri Tekrar Kullanma Sıklığı:",
    ["Hiç", "Nadiren", "Genellikle", "Her zaman"],
    index=2,
)
atık_ayristirma = st.sidebar.radio(
    "6. Geri Dönüşüm Kutusu Kullanıyor musunuz?", ["EVET", "HAYIR"], index=1
)

# 3. ULAŞIM VE MOBİLİTE (Soru 7, 8, 9, 10)
st.sidebar.subheader("🚘 Ulaşım ve Mobilite")
arac_km = st.sidebar.select_slider(
    "7. Şahsi Araç Haftalık Mesafe:",
    options=["0-100 km", "101-200 km", "201-300 km", "300+ km"],
    value="0-100 km",
)
yakit_turu = st.sidebar.selectbox(
    "8. Araç Yakıt Türü:", ["Aracım yok", "Benzin", "Dizel", "Lpg", "Elektrik"]
)
dolmus_sefer = st.sidebar.number_input(
    "9. Haftalık Dolmuş/Otobüs Kullanım Sayısı:", min_value=0, value=2, step=1
)
ulasim_tercihi = st.sidebar.selectbox(
    "10. İş/Okula Gidiş Ulaşım Türü:",
    ["Yürüyerek", "Toplu taşıma", "Özel araç"],
)

# 4. ISINMA VE ENERJİ (Soru 11, 12)
st.sidebar.subheader("🔥 Isınma ve Enerji Tüketimi")
isinma_yontemi = st.sidebar.selectbox(
    "11. Evde Isınma Yöntemi:",
    ["Doğalgaz", "Kömür", "Fındık kabuğu/Odun", "Elektrik"],
)
fatura_dilimi = st.sidebar.selectbox(
    "12. Aylık Ortalama Elektrik Faturası:",
    [
        "500 TL den az",
        "500-1000 TL",
        "1001-2000 TL",
        "2001-3000 TL",
        "3000 + TL",
    ],
    index=1,
)

# 5. BESLENME, TARIM VE BALIKÇILIK (Soru 13, 14, 15, 16, 17)
st.sidebar.subheader("🌾 Beslenme, Tarım ve Balıkçılık")
kirmizi_et = st.sidebar.selectbox(
    "13. Haftalık Kırmızı Et Tüketimi (Öğün):",
    ["0", "1-2", "3-5", "5+"],
    index=1,
)
yerel_gida = st.sidebar.selectbox(
    "14. Yerel Üretici / Pazar Alışveriş Oranı:",
    ["0%", "25%", "50%", "75%", "100%"],
    index=2,
)
zuruf_kullanimi = st.sidebar.radio(
    "15. Fındık Zürufu / Kabuğu Değerlendirme:", ["Evet", "Hayır"], index=0
)
gubre_torba = st.sidebar.number_input(
    "16. Yıllık Kimyasal Gübre Tüketimi (Torba):", min_value=0, value=4, step=1
)
tekne_yakit = st.sidebar.number_input(
    "17. Balıkçı Teknesi Haftalık Yakıtı (Litre):", min_value=0, value=0, step=5
)

# ---------------------------------------------------------
# HESAPLAMA MATEMATİĞİ VE KATSAYILAR
# ---------------------------------------------------------

# 1. Atık Skoru (Px)
r_atık = 0.25 if atık_ayristirma == "EVET" else 0.0
r_tekrar = (
    0.15
    if tekrar_kullanim == "Her zaman"
    else (0.10 if tekrar_kullanim == "Genellikle" else 0.0)
)
P_x = (poset_adedi * 2.5) * (1 - r_atık - r_tekrar)

# 2. Ulaşım Skoru (Uy)
km_katsayi = {
    "0-100 km": 20,
    "101-200 km": 50,
    "201-300 km": 80,
    "300+ km": 120,
}[arac_km]
yakit_katsayi = {
    "Aracım yok": 0,
    "Benzin": 1.2,
    "Dizel": 1.4,
    "Lpg": 0.9,
    "Elektrik": 0.3,
}[yakit_turu]
U_y = (km_katsayi * yakit_katsayi) + (dolmus_sefer * 3)

# 3. Enerji Skoru (Iz)
isinma_katsayi = {
    "Kömür": 120,
    "Doğalgaz": 50,
    "Elektrik": 70,
    "Fındık kabuğu/Odun": 15,
}[isinma_yontemi]
fatura_katsayi = {
    "500 TL den az": 20,
    "500-1000 TL": 45,
    "1001-2000 TL": 80,
    "2001-3000 TL": 120,
    "3000 + TL": 160,
}[fatura_dilimi]
I_z = (isinma_katsayi + fatura_katsayi) / hane_halki

# 4. Tarım Skoru (Tw)
zuruf_indirim = 100 if zuruf_kullanimi == "Evet" else 0
T_w = max(0, (gubre_torba * 18) - zuruf_indirim)

# 5. Beslenme ve Balıkçılık Skoru (Bg)
et_katsayi = {"0": 0, "1-2": 25, "3-5": 60, "5+": 100}[kirmizi_et]
gida_indirim = {
    "0%": 0,
    "25%": 10,
    "50%": 25,
    "75%": 40,
    "100%": 60,
}[yerel_gida]
B_g = max(0, et_katsayi + (tekne_yakit * 1.5) - gida_indirim)

# AĞIRLIKLI ANA FORMÜL (100 Üzerinden Ölçeklendirilmiş)
karbon_skoru = (
    (0.30 * I_z) + (0.20 * T_w) + (0.20 * U_y) + (0.15 * P_x) + (0.15 * B_g)
)

# ---------------------------------------------------------
# ARAYÜZ VE SİMÜLASYON
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.metric(
        label="Hesaplanan Bireysel Karbon Skoru",
        value=f"{round(karbon_skoru, 1)} Puan",
    )

    if karbon_skoru < 45:
        st.success("🟢 **Sınıflandırma:** Düşük Risk (Yeşil)")
    elif 45 <= karbon_skoru <= 95:
        st.warning("🟡 **Sınıflandırma:** Orta Risk (Sarı)")
    else:
        st.error("🔴 **Sınıflandırma:** Kritik Risk (Kırmızı)")

with col2:
    st.subheader("🔍 Modül Bazlı Emisyon Katkı Dağılımı")
    modul_df = pd.DataFrame(
        {
            "Modül": [
                "Isınma/Enerji",
                "Tarım/Ekosistem",
                "Ulaşım",
                "Plastik/Atık",
                "Beslenme/Balıkçılık",
            ],
            "Katkı Skoru": [
                round(0.30 * I_z, 1),
                round(0.20 * T_w, 1),
                round(0.20 * U_y, 1),
                round(0.15 * P_x, 1),
                round(0.15 * B_g, 1),
            ],
        }
    )
    st.bar_chart(modul_df.set_index("Modül"))

st.markdown("---")
st.subheader("💡 Eco-Algoritma Dinamik Karar Destek Senaryoları")

senaryolar = []

if isinma_yontemi == "Kömür":
    senaryolar.append(
        "🔥 **Isınma Senaryosu:** Kömür kullanımı yüksek emisyon üretir. Eynesil'in yerel biyokütle kaynağı olan **fındık kabuğuna** geçmek ısınma skorunuzu düşürecektir."
    )

if zuruf_kullanimi == "Hayır" and gubre_torba > 2:
    senaryolar.append(
        "🌱 **Tarım Senaryosu:** Kimyasal gübre kullanımınız yüksek. Atık **fındık zürufunu kompostlaştırarak** toprağa geri kazandırmak skorunuza 100 puanlık karbon yutağı indirimi sağlar."
    )

if yerel_gida in ["0%", "25%"]:
    senaryolar.append(
        "🛒 **Yerel Gıda Senaryosu:** Mutfak alışverişinizde **Eynesil ilçe pazarını ve yerel üreticileri** tercih etmek gıda lojistiği kaynaklı karbon yükünüzü azaltacaktır."
    )

if atık_ayristirma == "HAYIR":
    senaryolar.append(
        "♻️ **Atık Senaryosu:** Evsel atıklarınızı (cam/kağıt/plastik) ayrıştırarak geri dönüşüm kutularına atmak atık emisyonunuza %25 indirim sağlar."
    )

if senaryolar:
    for s in senaryolar:
        st.info(s)
else:
    st.balloons()
    st.success("🎉 Tüketim ve yaşam alışkanlıklarınız Eynesil iklim hedefleriyle tam uyumludur.")
