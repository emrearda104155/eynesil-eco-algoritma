"""Eco-Algoritma V2: herkes için sade veri giriş arayüzü.
Çalıştır: streamlit run eco_algoritma_v2_sade.py
Önemli: yalnızca kapsama alınan ve miktarı bilinen faaliyetlerin KISMİ emisyonu hesaplanır.
"""
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Eco-Algoritma | Kolay Karbon Hesabı", page_icon="🌱", layout="centered")
st.title("🌱 Eynesil Karbon Hesabım")
st.write("Günlük yaşamınızla ilgili birkaç soruya cevap verin. Bilmediğiniz soruları geçebilirsiniz.")
st.caption("Bu bir araştırma uygulamasıdır. Hesaplanan değerler bütün karbon ayak izinizi temsil etmeyebilir.")

FACTORS = {"Elektrik": 0.469, "Doğalgaz": 2.02633, "Kömür": 2.90495234,
           "Benzin": 2.075, "Dizel": 2.58354, "LPG": 1.55713}
STEPS = ["🏠 Ev ve elektrik", "🚗 Ulaşım", "🌿 Tarım", "♻️ Plastik", "🐟 Yerel faaliyetler", "📊 Sonucum"]
if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}
a = st.session_state.answers

def choice(key, label, options):
    old = a.get(key, options[0])
    a[key] = st.radio(label, options, index=options.index(old) if old in options else 0, key=f"widget_{key}")
    return a[key]

def number(key, label, unit, default=0.0):
    a[key] = st.number_input(f"{label} ({unit})", min_value=0.0, value=float(a.get(key, default)), step=1.0, key=f"widget_{key}")
    return a[key]

st.progress(st.session_state.step / (len(STEPS)-1))
st.caption(f"Adım {st.session_state.step+1} / {len(STEPS)}")
st.subheader(STEPS[st.session_state.step])

s = st.session_state.step
if s == 0:
    c = choice("electric_mode", "Elektrik faturanızdaki aylık kWh miktarını biliyor musunuz?", ["Bilmiyorum", "Evet", "Elektrik kullanmıyorum"])
    if c == "Evet": number("electric_kwh", "Ayda ortalama kaç kWh elektrik tüketiyorsunuz?", "kWh")
    st.divider()
    heat = choice("heat", "Evinizde en çok hangi ısınma türünü kullanıyorsunuz?", ["Bilmiyorum", "Doğalgaz", "Kömür", "Elektrik", "Odun / fındık kabuğu", "Diğer", "Isınma kullanmıyorum"])
    if heat == "Doğalgaz":
        if choice("gas_known", "Doğalgaz tüketiminizi biliyor musunuz?", ["Bilmiyorum", "Evet"]) == "Evet":
            number("gas_month", "Ayda ortalama kaç m³ doğalgaz kullanıyorsunuz?", "m³")
            st.caption("Yıl boyunca aynı tüketim olmuyorsa 12 aylık toplamı araştırmacı ekranında düzeltmek gerekir.")
    elif heat == "Kömür":
        if choice("coal_known", "Bir yılda kullandığınız kömür miktarını biliyor musunuz?", ["Bilmiyorum", "Evet"]) == "Evet": number("coal_year", "Bir yılda yaklaşık kaç kg kömür kullanıyorsunuz?", "kg")
    elif heat == "Odun / fındık kabuğu":
        st.info("Biyokütle kullanımı kaydedildi. Uygun hesaplama yöntemi tamamlanana kadar emisyon toplamına eklenmeyecek.")
elif s == 1:
    car = choice("car", "Özel araç kullanıyor musunuz?", ["Hayır", "Evet", "Bilmiyorum"])
    if car == "Evet":
        fuel = choice("car_fuel", "Aracınızın yakıtı nedir?", ["Benzin", "Dizel", "LPG", "Elektrik", "Bilmiyorum"])
        if fuel in ("Benzin", "Dizel", "LPG"):
            mode = choice("car_measure", "Hangisini söylemek daha kolay?", ["Bilmiyorum", "Haftalık kullandığım yakıt (litre)", "Haftalık yol (km) ve aracın tüketimi"])
            if mode == "Haftalık kullandığım yakıt (litre)": number("car_liters_week", "Haftada yaklaşık kaç litre yakıt alıyorsunuz?", "litre")
            elif mode == "Haftalık yol (km) ve aracın tüketimi":
                number("car_km_week", "Haftada yaklaşık kaç kilometre yol yapıyorsunuz?", "km")
                number("car_per100", "Aracınız 100 kilometrede kaç litre yakıyor?", "L/100 km")
        elif fuel == "Elektrik": st.info("Elektrikli araç şarjı ev elektrik faturasında yer alıyorsa ikinci kez sayılmayacaktır.")
    st.caption("Toplu taşıma alışkanlıkları sonraki araştırma sürümünde, uygun yolcu-km faktörleriyle hesaplanacaktır.")
elif s == 2:
    farming = choice("farming", "Fındık veya çay tarımıyla ilgileniyor musunuz?", ["Hayır", "Evet", "Bilmiyorum"])
    if farming == "Evet":
        fertilizer = choice("fertilizer", "Kimyasal gübre kullanıyor musunuz?", ["Hayır", "Evet", "Bilmiyorum"])
        if fertilizer == "Evet":
            if choice("fert_known", "Gübrenizin miktarını ve azot oranını biliyor musunuz?", ["Bilmiyorum", "Evet"]) == "Evet":
                number("bags", "Bir yılda kaç torba gübre kullanıyorsunuz?", "torba")
                number("bag_kg", "Bir torba kaç kilogram?", "kg")
                number("nitrogen_pct", "Gübre paketindeki ilk N (azot) oranı kaç?", "%")
                st.caption("Örnek: 20-20-0 yazıyorsa azot oranı %20'dir.")
        choice("residue", "Fındık zürufunu genellikle ne yapıyorsunuz?", ["Züruf oluşmuyor", "Bahçede bırakıyorum", "Kompost yapıyorum", "Yakıyorum", "Diğer / bilmiyorum"])
        st.caption("Züruf için henüz doğrulanmış yerel emisyon hesabı bulunmadığından yanıtınız kayıt amaçlıdır.")
elif s == 3:
    plastic = choice("plastic", "Plastik poşet ve şişe tüketiminizi belirtmek ister misiniz?", ["Bilmiyorum / geç", "Evet", "Kullanmıyorum"])
    if plastic == "Evet":
        number("bags_week", "Haftada yaklaşık kaç plastik poşet kullanıyorsunuz?", "adet")
        number("bottles_week", "Haftada yaklaşık kaç plastik su şişesi kullanıyorsunuz?", "adet")
        st.caption("Adet bilgisi kaydedilir. Malzeme türü ve ürün ağırlığı doğrulanmadan emisyon hesabına eklenmez.")
elif s == 4:
    fish = choice("fishing", "Balıkçı teknesi kullanıyor veya teknenin yakıtından sorumlu musunuz?", ["Hayır", "Evet", "Bilmiyorum"])
    if fish == "Evet":
        boat_fuel = choice("boat_fuel", "Tekne hangi yakıtı kullanıyor?", ["Dizel", "Benzin", "Bilmiyorum"])
        if boat_fuel != "Bilmiyorum":
            if choice("boat_known", "Haftalık yakıt miktarını biliyor musunuz?", ["Bilmiyorum", "Evet"]) == "Evet":
                number("boat_week", "Haftada ortalama kaç litre yakıt kullanılıyor?", "litre")
                st.caption("Tekne yakıtı yalnızca bu faaliyet sizin hesaplama kapsamınızdaysa dahil edilmelidir.")
    st.info("Beslenme emisyonları için kilogram cinsinden tüketim ve kapsamı doğrulanmış faktörler gereklidir. Bu kolay sürümde eksik bilgiyle tahmin yapılmaz.")
else:
    rows, gaps = [], []
    def add(label, module, amount, ef):
        if amount > 0: rows.append({"Faaliyet": label, "Modül": module, "Emisyon (kg CO₂e/yıl)": amount * ef})
    if a.get("electric_mode") == "Evet": add("Elektrik", "Enerji", a.get("electric_kwh", 0)*12, FACTORS["Elektrik"])
    elif a.get("electric_mode") == "Bilmiyorum": gaps.append("Elektrik tüketimi")
    if a.get("heat") == "Doğalgaz":
        if a.get("gas_known") == "Evet": add("Doğalgaz (aylık ortalama ×12)", "Enerji", a.get("gas_month",0)*12, FACTORS["Doğalgaz"])
        else: gaps.append("Doğalgaz tüketimi")
    elif a.get("heat") == "Kömür":
        if a.get("coal_known") == "Evet": add("Kömür", "Enerji", a.get("coal_year",0), FACTORS["Kömür"])
        else: gaps.append("Kömür tüketimi")
    elif a.get("heat") in ("Odun / fındık kabuğu", "Diğer", "Bilmiyorum"): gaps.append("Isınma türü veya biyokütle emisyonu")
    if a.get("car") == "Evet":
        f = a.get("car_fuel")
        if f in ("Benzin", "Dizel", "LPG"):
            mode = a.get("car_measure")
            if mode == "Haftalık kullandığım yakıt (litre)": add("Özel araç", "Ulaşım", a.get("car_liters_week",0)*52, FACTORS[f])
            elif mode == "Haftalık yol (km) ve aracın tüketimi": add("Özel araç", "Ulaşım", a.get("car_km_week",0)*52*a.get("car_per100",0)/100, FACTORS[f])
            else: gaps.append("Özel araç yakıt tüketimi")
        else: gaps.append("Özel araç enerji tüketimi")
    if a.get("farming") == "Evet":
        if a.get("fertilizer") == "Evet":
            if a.get("fert_known") == "Evet" and a.get("bag_kg",0)>0 and a.get("nitrogen_pct",0)>0:
                n = a.get("bags",0)*a["bag_kg"]*a["nitrogen_pct"]/100
                add("Gübre kaynaklı doğrudan N₂O", "Tarım", n, 0.010*(44/28)*273)
                gaps.append("Gübrenin dolaylı N₂O ve üretim emisyonları")
            else: gaps.append("Gübre azot miktarı")
        if a.get("residue") not in (None, "Züruf oluşmuyor"): gaps.append("Fındık zürufu yönetimi")
    if a.get("plastic") == "Evet" and (a.get("bags_week",0)>0 or a.get("bottles_week",0)>0): gaps.append("Plastik malzeme ağırlığı/türü")
    if a.get("fishing") == "Evet":
        if a.get("boat_fuel") in ("Dizel", "Benzin") and a.get("boat_known") == "Evet":
            add("Balıkçı teknesi yakıtı", "Yerel faaliyet", a.get("boat_week",0)*52, FACTORS[a["boat_fuel"]])
        else: gaps.append("Balıkçı teknesi yakıtı")
    gaps.extend(["Toplu taşıma", "Gıda tüketimi", "Atık bertarafı ve geri dönüşüm"])
    total = sum(r["Emisyon (kg CO₂e/yıl)"] for r in rows)
    st.metric("Hesaplanabilen emisyon", f"{total:,.1f} kg CO₂e/yıl")
    st.warning("Bu sonuç **kısmi hesaplamadır**. Bilinmeyen veya henüz hesaplanamayan faaliyetler sıfır kabul edilmemiştir.")
    if rows:
        df = pd.DataFrame(rows)
        st.bar_chart(df.groupby("Modül")["Emisyon (kg CO₂e/yıl)"].sum())
        st.write("En yüksek hesaplanan kaynak:", df.sort_values("Emisyon (kg CO₂e/yıl)", ascending=False).iloc[0]["Faaliyet"])
    else: st.info("Henüz sayısal emisyon hesaplanabilecek yeterli bilgi verilmedi.")
    with st.expander("Eksik kalan hesaplamalar"):
        for g in dict.fromkeys(gaps): st.write("•", g)
    with st.expander("🔬 Araştırmacılar için hesaplama ayrıntıları"):
        st.caption("Elektrik: Türkiye EVÇED 2023 dağıtım tüketim noktası faktörü 0,469 kg CO₂e/kWh. Yakıtlar: DESNZ 2026 Birleşik Krallık doğrudan yakıt emisyon faktörleri; Türkiye'ye özgü ölçümler değildir. Gübre: IPCC 2019 genel doğrudan N₂O EF₁=0,010; N₂O GWP100=273. Diğer yaşam döngüsü bileşenleri eksik olabilir.")
        if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.write("**Varsayımsal azaltım senaryosu:**")
        reduction = st.slider("Hesaplanan elektrik ve özel araç tüketiminde azaltım (%)", 0, 50, 10, 5)
        eligible = sum(r["Emisyon (kg CO₂e/yıl)"] for r in rows if r["Faaliyet"] in ("Elektrik", "Özel araç"))
        st.write(f"Bu iki faaliyette tahmini doğrudan azaltım: **{eligible*reduction/100:,.1f} kg CO₂e/yıl**")
        st.caption("Başka faaliyete geçişin emisyonları ve maliyetler dahil değildir; gerçekleşmiş tasarruf değildir.")
    st.download_button("Yanıtlarımı CSV olarak indir", data=pd.DataFrame([a]).to_csv(index=False).encode("utf-8-sig"), file_name="eco_algoritma_yanitlar.csv", mime="text/csv")

st.divider()
left, right = st.columns(2)
with left:
    if st.button("← Geri", disabled=s==0, use_container_width=True):
        st.session_state.step -= 1
        st.rerun()
with right:
    if st.button("Sonucumu gör" if s==4 else "İleri →", disabled=s==5, type="primary", use_container_width=True):
        st.session_state.step += 1
        st.rerun()
