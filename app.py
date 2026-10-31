"""Eco-Algoritma V2 — kaynaklı yakıt, gübre N₂O, züruf ve plastik malzeme hesabı.
Çalıştırma: streamlit run eco_algoritma_v2_karsilastirma.py
"""
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Eco-Algoritma V2 | Eynesil", page_icon="🌱", layout="wide")
st.title("🌱 Eco-Algoritma V2 — Eynesil Karbon Hesaplama")
st.caption("Araştırma prototipi | Gerçek tüketim × doğrulanmış emisyon faktörü | Yıllık kg CO₂e")
st.info("Elektrik: Türkiye EVÇED 2023 dağıtım hattı faktörü. Doğalgaz, konut kömürü, benzin, dizel ve LPG: DESNZ 2026 Birleşik Krallık doğrudan yakıt emisyon faktörleri (Türkiye için referans/proksi). Diğer faaliyetlerde doğrulanmamış katsayı otomatik atanmaz.")

DESNZ_2026_URL = "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026"
FUEL_FACTORS = {
    "Doğalgaz": {"value": 2.02633, "unit": "m³", "row": "Fuels!D40", "detail": "Natural gas"},
    "Kömür": {"value": 2.90495234, "unit": "kg", "row": "Fuels!D137", "detail": "Coal (domestic)"},
    "Benzin": {"value": 2.07500, "unit": "litre", "row": "Fuels!D96", "detail": "Petrol (average biofuel blend)"},
    "Dizel": {"value": 2.58354, "unit": "litre", "row": "Fuels!D72", "detail": "Diesel (average biofuel blend)"},
    "LPG": {"value": 1.55713, "unit": "litre", "row": "Fuels!D36", "detail": "LPG"},
}

def fuel_factor(label, fuel, key):
    meta = FUEL_FACTORS[fuel]
    method = st.radio(f"{label} — emisyon faktörü", ["DESNZ 2026 referansı", "Başka kaynak — elle gir"], key=f"{key}_method", horizontal=True)
    if method == "DESNZ 2026 referansı":
        st.caption(f"{fuel}: {meta['value']:.5f} kg CO₂e/{meta['unit']} · {meta['detail']} · {meta['row']} · doğrudan yakıt kullanımı · Birleşik Krallık referansı · [DESNZ 2026]({DESNZ_2026_URL})")
        return meta["value"]
    return factor(label, meta["unit"], key)



def qty(label, value=0.0, key=None):
    return st.number_input(label, min_value=0.0, value=float(value), step=1.0, key=key)


def factor(label, unit, key):
    a, b = st.columns([1, 1.5])
    with a:
        f = st.number_input(f"{label} (kg CO₂e/{unit})", min_value=0.0, value=None, format="%.6f", key=f"{key}_factor", help="Boş bırakılırsa hesaplanmaz. 0 ancak kaynakla gerekçelendirilmişse girilmelidir.")
    with b:
        src = st.text_input(f"{label} — faktör kaynağı / yıl / kapsam", key=f"{key}_source", placeholder="Kurum, yayın yılı, tablo, kapsam")
    return f if f is not None and src.strip() else None


results = []
missing = []


def add(activity, module, amount, unit, ef, required=True):
    if amount == 0:
        results.append({"Modül": module, "Faaliyet": activity, "Miktar": 0.0, "Birim": unit, "Emisyon (kg CO₂e/yıl)": 0.0})
    elif ef is None:
        missing.append(f"{module} / {activity}: uygun emisyon faktörü ve kaynağı eksik")
    else:
        results.append({"Modül": module, "Faaliyet": activity, "Miktar": amount, "Birim": unit, "Emisyon (kg CO₂e/yıl)": amount * ef})


with st.expander("1. Isınma ve enerji", expanded=True):
    st.write("Elektrikli ısıtma toplam elektrik tüketimindeyse tekrar eklemeyin. Yakıtları yıllık fiziksel miktar olarak girin.")
    electricity_month = qty("Aylık elektrik tüketimi (kWh)", key="elec")
    electric_source = st.radio("Elektrik emisyon faktörü yöntemi", ["Resmî EVÇED 2023 — dağıtım hattı (0,469 kg CO₂e/kWh)", "Başka kaynak / yıl — elle gir"], horizontal=True)
    if electric_source.startswith("Resmî"):
        ef_elec = 0.469
        st.caption("Kaynak: T.C. Enerji ve Tabii Kaynaklar Bakanlığı, EVÇED, Türkiye Elektrik Üretimi ve Elektrik Tüketim Noktası Emisyon Faktörleri, hesaplama dönemi 2023, dağıtım hattı tüketim noktası. https://duyuru.enerji.gov.tr/evced-cevre-ve-iklim-elektrik-uretim-tuketim-emisyon-faktorleri")
    else:
        ef_elec = factor("Elektrik", "kWh", "elec")
    add("Elektrik", "Enerji", electricity_month * 12, "kWh", ef_elec)
    gas = qty("Yıllık doğalgaz tüketimi (m³)", key="gas")
    ef_gas = fuel_factor("Doğalgaz", "Doğalgaz", "gas")
    add("Doğalgaz", "Enerji", gas, "m³", ef_gas)
    coal = qty("Yıllık kömür tüketimi (kg)", key="coal")
    ef_coal = fuel_factor("Kömür", "Kömür", "coal")
    add("Kömür", "Enerji", coal, "kg", ef_coal)
    st.info("Odun/fındık kabuğu: biyojenik CO₂'nin ayrı raporlanması ve CH₄/N₂O hesap sınırları netleşene kadar otomatik toplam hesabına alınmıyor.")
    biomass = qty("Yıllık odun / fındık kabuğu tüketimi (kg) — kayıt amaçlı", key="biomass")
    if biomass > 0:
        missing.append("Enerji / Biyokütle: uygun IPCC gaz ayrımı ve faktörleriyle hesaplama henüz eklenmedi")

with st.expander("2. Tarım ve ekosistem — IPCC 2019 doğrudan N₂O"):
    st.write("Azotlu gübre kaynaklı **doğrudan N₂O** emisyonu hesaplanır. Dolaylı N₂O, gübre üretimi ve züruf emisyonları bu hesabın dışındadır.")
    bags = qty("Yıllık gübre torbası (adet)", key="bags")
    bag_mass = qty("Torba ağırlığı (kg/torba)", key="bag_mass")
    n_percent = st.number_input("Gübrenin azot oranı (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, help="Örnek: NPK 20-20-0 gübresinin azot oranı %20'dir. Gübre etiketinden kontrol edin.")
    n_applied = bags * bag_mass * n_percent / 100
    st.metric("Toprağa uygulanan azot (kg N/yıl)", f"{n_applied:,.2f}")

    ef_choice = st.radio(
        "IPCC 2019 EF₁ seçimi (kg N₂O-N / kg N)",
        ["Genel varsayılan: 0,010", "Nemli iklimde sentetik gübre: 0,016", "Başka doğrulanmış değer"],
        horizontal=False,
        help="Nemli iklim faktörünü ancak bölge ve gübre sınıflandırması gerekçelendirildiğinde seçin.",
    )
    if ef_choice.startswith("Genel"):
        ef1 = 0.010
    elif ef_choice.startswith("Nemli"):
        ef1 = 0.016
    else:
        ef1 = st.number_input("EF₁ (kg N₂O-N/kg N)", min_value=0.0, value=None, format="%.5f", key="ag_ef1_custom")
        ef1_source = st.text_input("EF₁ kaynağı, yılı ve kapsamı", key="ag_ef1_source")
        if not ef1_source.strip():
            ef1 = None

    gwp = st.number_input("N₂O için 100 yıllık GWP (IPCC AR6 varsayılanı)", min_value=0.0, value=273.0, step=1.0, help="AR6 N₂O GWP100 = 273. Karşılaştırılan diğer faktörlerin gaz ve GWP kapsamını kontrol edin.")
    st.caption("Kaynak: IPCC 2019 Refinement, Cilt 4, Bölüm 11, Tablo 11.1; genel EF₁=0,010, nemli iklim sentetik gübre EF₁=0,016. https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/4_Volume4/19R_V4_Ch11_Soils_N2O_CO2.pdf")
    st.latex(r"E_{\mathrm{dogrudan\ N_2O}} = N_{\mathrm{uygulanan}} \times EF_1 \times \frac{44}{28} \times GWP_{N_2O}")
    if bags > 0 and (bag_mass == 0 or n_percent == 0):
        missing.append("Tarım / Gübre: torba ağırlığı veya gübrenin azot yüzdesi girilmedi")
    elif n_applied > 0 and ef1 is None:
        missing.append("Tarım / Gübre: EF₁ değeri ve kaynak bilgisi eksik")
    elif n_applied > 0:
        direct_n2o_n = n_applied * ef1
        direct_n2o = direct_n2o_n * 44 / 28
        direct_co2e = direct_n2o * gwp
        st.metric("Doğrudan gübre N₂O emisyonu (kg CO₂e/yıl)", f"{direct_co2e:,.2f}")
        st.caption(f"Ara hesap: {direct_n2o_n:.4f} kg N₂O-N → {direct_n2o:.4f} kg N₂O → {direct_co2e:.2f} kg CO₂e/yıl")
        results.append({"Modül": "Tarım", "Faaliyet": "Gübre — doğrudan N₂O", "Miktar": n_applied, "Birim": "kg N/yıl", "Emisyon (kg CO₂e/yıl)": direct_co2e})
        missing.append("Tarım / Gübre: dolaylı N₂O ve gübre üretimi kaynaklı emisyonlar kapsam dışında")

    st.markdown("**Fındık zürufu yönetimi — IPCC yöntem değerlendirmesi**")
    st.caption("Fındık zürufu (hasat artığı), ısınmada kullanılan fındık kabuğundan ayrı kaydedilir. Aynı malzeme iki modülde sayılmaz.")
    zuruf = st.selectbox("Fındık zürufu yönetimi", ["Faaliyet yok", "Kompost", "Açıkta yakma", "Bahçede bırakma", "Diğer / bilinmiyor"])
    zuruf_kg = qty("Yıllık yönetilen züruf miktarı (kg, yaş ağırlık)", key="zuruf")
    if zuruf_kg > 0 and zuruf == "Faaliyet yok":
        st.warning("Züruf miktarı sıfırdan büyükken yönetim biçimi 'Faaliyet yok' seçildi. Yönetim biçimini düzeltin.")
        missing.append("Tarım / Züruf: yönetim biçimi belirtilmedi")
    elif zuruf_kg > 0 and zuruf == "Kompost":
        st.info("IPCC 2006 Cilt 5 Bölüm 4 Tablo 4.1'de **genel organik atık kompostu** için yaş ağırlık bazında CH₄=4 kg/ton ve N₂O=0,24 kg/ton varsayılanları bulunur. Bunlar fındık zürufuna özgü ölçülmüş faktörler değildir.")
        use_proxy = st.checkbox("Genel IPCC kompost faktörleriyle yalnızca keşif amaçlı örnek hesaplamayı göster (resmî toplamdan hariç)", value=False)
        if use_proxy:
            ch4_gwp = st.number_input("CH₄ GWP₁₀₀ (seçilen raporlama yaklaşımı)", min_value=0.0, value=27.2, step=0.1, key="ch4_gwp", help="AR6 biyojenik metan için örnek GWP100=27,2; metodolojik tutarlılık kontrol edilmelidir.")
            compost_ch4 = zuruf_kg / 1000 * 4
            compost_n2o = zuruf_kg / 1000 * 0.24
            compost_co2e = compost_ch4 * ch4_gwp + compost_n2o * gwp
            st.metric("Kompost — örnek süreç emisyonu (toplamdan hariç)", f"{compost_co2e:,.2f} kg CO₂e/yıl")
            st.caption(f"{compost_ch4:.4f} kg CH₄ × {ch4_gwp:g} + {compost_n2o:.4f} kg N₂O × {gwp:g}. Yalnızca kompostlama sürecinin CH₄ ve N₂O gazları; önlenen gübre üretimi, toprak karbonu ve diğer yaşam döngüsü etkileri dahil değildir.")
        missing.append("Tarım / Züruf: genel kompost varsayılanlarının fındık zürufuna uygunluğu doğrulanmadı; toplamdan hariç")
    elif zuruf_kg > 0 and zuruf == "Açıkta yakma":
        st.warning("Açıkta yakma için tarımsal kalıntı yakımı ile belediye katı atığı yakımı farklı IPCC kategorileridir. Belediye atığı katsayıları fındık zürufuna doğrudan uygulanamaz. Kuru madde oranı, yakılan pay ve uygun CH₄/N₂O faktörleri belirlenmeden sonuç hesaplanmaz.")
        missing.append("Tarım / Züruf: açıkta yakma için tarımsal kalıntıya uygun faktör ve kuru madde verisi eksik")
    elif zuruf_kg > 0 and zuruf == "Bahçede bırakma":
        st.info("Bahçede bırakılan züruf için bozunma, toprağa azot girdisi ve olası toprak karbonu etkileri ayrıca modellenmelidir; otomatik sıfır emisyon veya karbon yutağı kabul edilmez.")
        missing.append("Tarım / Züruf: bahçede bırakma için uygun toprak/kalıntı hesap yöntemi eksik")
    elif zuruf_kg > 0:
        missing.append("Tarım / Züruf: yönetim türü ve uygun hesap yöntemi eksik")
    st.caption("Kaynak: IPCC 2006 Cilt 5 Bölüm 4, Tablo 4.1 (genel kompostlama); IPCC 2006 Cilt 4 ve IPCC 2019 güncellemesi (tarımsal kalıntı/toprak yönetimi). https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/5_Volume5/V5_4_Ch4_Bio_Treat.pdf")

with st.expander("3. Ulaşım ve mobilite"):
    km_week = qty("Özel araçla haftalık mesafe (km)", key="km_week")
    consumption = qty("Araç tüketimi (L/100 km)", key="consumption")
    fuel = st.selectbox("Araç yakıtı", ["Benzin", "Dizel", "LPG"])
    annual_liters = km_week * 52 * consumption / 100
    st.caption(f"Yıllık hesaplanan yakıt: {annual_liters:,.2f} litre (52 hafta varsayımı)")
    ef_car = fuel_factor(f"{fuel} (araç)", fuel, "car")
    add(f"Özel araç — {fuel}", "Ulaşım", annual_liters, "litre", ef_car)
    transit = qty("Yıllık toplu taşıma mesafesi (yolcu-km)", key="transit")
    ef_transit = factor("Toplu taşıma", "yolcu-km", "transit")
    add("Toplu taşıma", "Ulaşım", transit, "yolcu-km", ef_transit)

with st.expander("4. Plastik ve atık yönetimi — malzeme üretimi"):
    st.write("Plastik poşet ve PET şişe sayıları, kullanıcı tarafından girilen **tek ürün ağırlıklarıyla** kg'a dönüştürülür. Buradaki sonuç **yalnızca birincil plastik malzeme üretimi** kapsamındadır; atığın toplanması, geri dönüşümü veya bertarafı dahil değildir.")
    st.caption("Referans: DESNZ 2025, Material use → Plastic → Primary material production; LDPE/LLDPE (incl. forming) = 2,96508 kg CO₂e/kg; PET (incl. forming) = 3,86390 kg CO₂e/kg. Birleşik Krallık referanslarıdır, Eynesil ölçümü değildir. https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025")
    st.warning("Poşetin LDPE/LLDPE, şişenin PET olduğu doğrulanmalı. Ambalaj kapağı, etiket, nakliye ve kullanım sonu bu malzeme hesabının dışındadır. Varsayılan ürün ağırlığı girilmez.")
    bag_count = st.number_input("Haftalık plastik poşet sayısı (adet)", min_value=0, value=0, step=1, key="bag_count")
    bag_grams = st.number_input("Bir poşetin ölçülen ağırlığı (gram)", min_value=0.0, value=0.0, step=0.5, key="bag_grams")
    bottle_count = st.number_input("Haftalık PET şişe sayısı (adet)", min_value=0, value=0, step=1, key="bottle_count")
    bottle_grams = st.number_input("Bir boş PET şişenin ölçülen ağırlığı (gram; kapak ve etiket hariç)", min_value=0.0, value=0.0, step=0.5, key="bottle_grams")
    bag_material_ok = st.checkbox("Poşet malzemesi LDPE/LLDPE olarak doğrulandı", key="bag_ok")
    bottle_material_ok = st.checkbox("Şişe gövdesi PET olarak doğrulandı", key="bottle_ok")
    bag_annual_kg = bag_count * 52 * bag_grams / 1000
    bottle_annual_kg = bottle_count * 52 * bottle_grams / 1000
    st.caption(f"Yıllık malzeme miktarı: poşet {bag_annual_kg:.3f} kg; PET şişe {bottle_annual_kg:.3f} kg (52 hafta varsayımı).")
    if bag_count > 0 and (bag_grams == 0 or not bag_material_ok):
        missing.append("Atık / Poşet: ölçülen gram ağırlığı ve LDPE/LLDPE malzeme doğrulaması gerekli")
    else:
        add("Poşet malzemesi — birincil üretim", "Atık", bag_annual_kg, "kg LDPE/LLDPE", 2.96508)
    if bottle_count > 0 and (bottle_grams == 0 or not bottle_material_ok):
        missing.append("Atık / PET: ölçülen gram ağırlığı ve PET malzeme doğrulaması gerekli")
    else:
        add("PET şişe gövdesi — birincil üretim", "Atık", bottle_annual_kg, "kg PET", 3.86390)
    st.info("Atık ayrıştırma veya geri dönüşüm tercihi otomatik yüzde indirim oluşturmaz. Geri dönüşüm ve bertaraf emisyonları için ayrıca uygun yöntem ve işlem verisi gereklidir.")
    st.caption("Metodoloji: DESNZ malzeme kullanım faktörleri satın alınan malzemenin üretim aşamasını temsil eder; toplanan atığın geri dönüştürülmesinden sağlanan faydayı doğrudan hesaplamaz.")

with st.expander("5. Beslenme ve yerel faaliyetler — gıda ve kıyı balıkçılığı"):
    st.write("Gıda tüketimi ile balıkçı teknesinin yakıtı **farklı faaliyetlerdir**. Gıdanın yaşam döngüsü emisyonu ve tekne yakıtı, kapsamları örtüşüyorsa birlikte toplanmamalıdır.")
    st.markdown("**Gıda tüketimi — kaynaklı faktörle hesaplama**")
    food_type = st.selectbox("Gıda ürünü", ["Sığır eti", "Koyun / kuzu eti", "Diğer kırmızı et", "Balık / deniz ürünü", "Diğer gıda"], key="food_type")
    food_kg = qty("Yıllık tüketim miktarı (kg ürün)", key="food")
    st.caption("Anketteki haftalık öğün sıklığı kg cinsinden kesin tüketim miktarı değildir. Gerçek yıllık kg miktarını girin.")
    ef_food = factor(f"{food_type} — ürün emisyon faktörü", "kg ürün", "food")
    food_scope = st.selectbox("Gıda emisyon faktörünün kapsamı", ["Belirtilmedi / doğrulanmadı", "Çiftlik kapısına kadar", "Tüketiciye kadar yaşam döngüsü", "Diğer (kaynakta açıklanmış)"], key="food_scope")
    if food_kg > 0 and food_scope == "Belirtilmedi / doğrulanmadı":
        missing.append("Beslenme / Gıda: emisyon faktörünün yaşam döngüsü kapsamı belirtilmedi")
    elif food_kg > 0 and ef_food is None:
        missing.append("Beslenme / Gıda: emisyon faktörü ve kaynak bilgisi eksik")
    else:
        add(f"Gıda — {food_type} ({food_scope})", "Beslenme", food_kg, "kg ürün", ef_food)

    st.markdown("**Kıyı balıkçılığı — tekne yakıtı**")
    st.caption("Tekne yakıtı tüketimini yalnızca balıkçılık faaliyetinin sorumluluk/kapsam sınırı tanımlandığında girin. Bu değer, satın alınan balığın tüm yaşam döngüsü emisyonuyla aynı toplamda iki kez sayılmamalıdır.")
    boat_liters = qty("Balıkçı teknesi yıllık yakıt tüketimi (litre)", key="boat")
    boat_fuel = st.selectbox("Tekne yakıt türü", ["Dizel", "Benzin"], key="boat_fuel")
    ef_boat = fuel_factor(f"Tekne {boat_fuel}", boat_fuel, "boat")
    st.checkbox("Tekne yakıtı gıda faktöründe zaten kapsanıyor / çifte sayım riski var", key="boat_overlap", value=False)
    if st.session_state.boat_overlap and boat_liters > 0:
        st.warning("Tekne yakıtı ayrı gösteriliyor ancak çifte sayımı önlemek için hesaplanan toplama eklenmiyor.")
        st.metric("Tekne yakıtı — ayrı bilgilendirme (kg CO₂e/yıl)", f"{boat_liters * ef_boat:,.2f}" if ef_boat is not None else "Faktör eksik")
        missing.append("Beslenme / Tekne: gıda yaşam döngüsü hesabıyla kapsam çakışması; toplama dahil edilmedi")
    else:
        add(f"Balıkçı teknesi — {boat_fuel} (doğrudan yakıt)", "Beslenme", boat_liters, "litre", ef_boat)

    st.markdown("**Yerel üretici tercihi — nitel gösterge**")
    local_share = st.slider("Yerel üreticiden temin edilen gıda oranı (%) — yalnızca anket göstergesi", 0, 100, 0, 5, key="local_share")
    st.caption(f"Yerel üretici tercih oranı: %{local_share}. Tek başına emisyon indirimi sayılmaz; üretim yöntemi, taşımacılık, depolama ve ürün türü verileri gerekir.")
    st.info("Gıda emisyon faktörleri için kaynak önerileri: bilimsel yaşam döngüsü değerlendirmeleri (LCA), AGRIBALYSE ve uygun kapsamlı resmî veri setleri. Farklı sınırları olan faktörler doğrudan karşılaştırılmamalıdır.")

st.divider()
st.subheader("📊 Hesaplama sonuçları")
if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)
    totals = df.groupby("Modül")["Emisyon (kg CO₂e/yıl)"].sum()
    if missing:
        st.warning("**Kısmi sonuç:** Aşağıdaki eksikler nedeniyle hesaplanan toplam, tam karbon ayak izi değildir.")
    else:
        st.success("Girilen faaliyetler için gerekli hesaplama girdileri mevcut. Kapsamın eksiksizliği ayrıca kontrol edilmelidir.")
    st.metric("Hesaplanabilen faaliyetlerin toplamı (kg CO₂e/yıl)", f"{totals.sum():,.2f}")
    st.bar_chart(totals)
else:
    st.info("Hesaplanan faaliyet henüz yok.")

if missing:
    with st.expander(f"⚠️ Eksik hesaplamalar ({len(missing)})", expanded=True):
        for item in missing:
            st.write("• " + item)

st.subheader("⚖️ Standart model – Eynesil yerel model karşılaştırması")
st.write("**Aynı kullanıcı, aynı tüketim miktarları ve aynı emisyon faktörleri** kullanılır. Standart kapsam genel faaliyetleri içerir; yerel kapsam buna hesaplanabilen kıyı balıkçılığı tekne yakıtını ekler. Fındık zürufu henüz hesaplanmadığı için her iki toplamın dışındadır.")
if results:
    compare_df = pd.DataFrame(results)
    boat_mask = compare_df["Faaliyet"].str.startswith("Balıkçı teknesi —")
    standard_total = float(compare_df.loc[~boat_mask, "Emisyon (kg CO₂e/yıl)"].sum())
    local_addition = float(compare_df.loc[boat_mask, "Emisyon (kg CO₂e/yıl)"].sum())
    local_total = standard_total + local_addition
    c1, c2, c3 = st.columns(3)
    c1.metric("Standart kapsam (kg CO₂e/yıl)", f"{standard_total:,.2f}")
    c2.metric("Yerel kapsam (kg CO₂e/yıl)", f"{local_total:,.2f}")
    c3.metric("Eklenen hesaplanabilir yerel faaliyet", f"{local_addition:,.2f}")
    st.bar_chart(pd.DataFrame({"Kapsam": ["Standart", "Yerel"], "Hesaplanabilen emisyon (kg CO₂e/yıl)": [standard_total, local_total]}).set_index("Kapsam"))
    if local_addition == 0:
        st.info("Bu veri girişinde hesaplamaya eklenebilen tekne yakıtı emisyonu yok. Modellerin eşit çıkması, Eynesil'e özgü diğer faaliyetlerin sıfır emisyonlu olduğunu göstermez.")
    if missing:
        st.warning("Her iki toplam da **kısmi hesaplama sonucudur**. Eksik faaliyetler sıfır emisyon kabul edilmemiş, karşılaştırma kapsamı dışında bırakılmıştır.")
    st.caption("Bu fark bir azaltım, tasarruf veya model doğruluğu üstünlüğü değildir; yalnızca ölçülebilen faaliyet kapsamının genişlemesinden doğan farktır. Balık yaşam döngüsü faktörü tekne yakıtını kapsıyorsa çifte sayımı önleme seçeneği bu eklemeyi dışarıda bırakır. Tarımda gübre kaynaklı doğrudan N₂O her iki kapsamda yer alır; züruf hesaplanmadığı için hiçbir kapsama eklenmez.")
else:
    st.info("Karşılaştırma için en az bir hesaplanabilir faaliyet girin.")

st.subheader("🔁 Sayısal azaltım senaryosu — özel araç")
reduction = st.slider("Özel araç mesafesinde varsayımsal azalma (%)", 0, 100, 20, 5)
if annual_liters > 0 and ef_car is not None:
    base = annual_liters * ef_car
    alternative = base * (1 - reduction / 100)
    st.write(f"Başlangıç: **{base:,.2f} kg CO₂e/yıl** · Alternatif: **{alternative:,.2f} kg CO₂e/yıl** · Fark: **{base-alternative:,.2f} kg CO₂e/yıl**")
    st.caption("Sadece özel araç yakıtı azalması hesaplanmıştır. Yerine geçen toplu taşımanın emisyonu bu senaryoda hesaplanmamıştır.")
else:
    st.info("Senaryo için araç mesafesi, yakıt tüketimi, emisyon faktörü ve faktör kaynağı girilmelidir.")



st.divider()
st.subheader("📈 Duyarlılık analizi — tek değişkenli ±%10")
st.write("Her seferinde yalnızca **bir faaliyet miktarı** %10 artırılıp azaltılır; diğer girdiler ve emisyon faktörleri sabit tutulur. Sonuçlar **hesaplanabilen faaliyetlerin kısmi toplamına** göredir. Bu analiz belirsizlik aralığı veya gerçekleşmiş tasarruf değildir.")

if results:
    sensitivity_df = pd.DataFrame(results)
    baseline_total = float(sensitivity_df["Emisyon (kg CO₂e/yıl)"].sum())
    sensitivity_items = [
        ("Elektrik tüketimi", "Elektrik"),
        ("Doğalgaz tüketimi", "Doğalgaz"),
        ("Kömür tüketimi", "Kömür"),
        ("Özel araç mesafesi", "Özel araç —"),
        ("Gübre miktarı (azot oranı sabit)", "Gübre — doğrudan N₂O"),
        ("Balıkçı teknesi yakıtı", "Balıkçı teknesi —"),
    ]
    sensitivity_rows = []
    for label, activity_prefix in sensitivity_items:
        matched = sensitivity_df[sensitivity_df["Faaliyet"].str.startswith(activity_prefix, na=False)]
        if matched.empty:
            continue  # Eksik faktörlü faaliyet hesaplanmış gibi gösterilmez.
        component_emission = float(matched["Emisyon (kg CO₂e/yıl)"].sum())
        if component_emission <= 0:
            continue
        delta = 0.10 * component_emission
        sensitivity_rows.append({
            "Değişken": label,
            "Başlangıç (kg CO₂e/yıl)": baseline_total,
            "−%10 tüketim (kg CO₂e/yıl)": baseline_total - delta,
            "+%10 tüketim (kg CO₂e/yıl)": baseline_total + delta,
            "Mutlak etki (± kg CO₂e/yıl)": delta,
            "Toplama göre etki (±%)": 100 * delta / baseline_total if baseline_total else 0.0,
        })
    if sensitivity_rows:
        sens = pd.DataFrame(sensitivity_rows).sort_values("Mutlak etki (± kg CO₂e/yıl)", ascending=False)
        st.dataframe(sens, use_container_width=True, hide_index=True, column_config={
            "Başlangıç (kg CO₂e/yıl)": st.column_config.NumberColumn(format="%.2f"),
            "−%10 tüketim (kg CO₂e/yıl)": st.column_config.NumberColumn(format="%.2f"),
            "+%10 tüketim (kg CO₂e/yıl)": st.column_config.NumberColumn(format="%.2f"),
            "Mutlak etki (± kg CO₂e/yıl)": st.column_config.NumberColumn(format="%.2f"),
            "Toplama göre etki (±%)": st.column_config.NumberColumn(format="%.2f"),
        })
        st.bar_chart(sens.set_index("Değişken")[["Mutlak etki (± kg CO₂e/yıl)"]])
        st.caption("Etki, faaliyet emisyonunun %10'udur: E'=E_toplam ± 0,10×E_faaliyet. Yakıt türü, gübre azot oranı ve emisyon faktörleri değişmez. Bu sıralama sadece girilen tüketim profili için geçerlidir.")
        if missing:
            st.warning("Bazı faaliyetlerin emisyon faktörleri veya hesaplama yöntemi eksik. Duyarlılık sonuçları yalnızca hesaplanan bileşenleri kapsar; eksikler sıfır varsayılmadı.")
    else:
        st.info("Duyarlılık analizi için elektrik, yakıt, araç mesafesi veya gübreye ilişkin hesaplanmış, sıfırdan büyük bir emisyon girin.")
else:
    st.info("Duyarlılık analizi için önce hesaplanabilir tüketim verisi girin.")



st.divider()
st.subheader("🎯 Azaltım senaryoları ve kısıtlı optimizasyon")
st.write("Bu araç, **hesaplanabilen faaliyetler** için tüketim azaltım potansiyelini karşılaştırır. Yüzdeler kullanıcı tarafından varsayılır; ölçülmüş tasarruf veya ekonomik optimum değildir.")

if results:
    opt_df = pd.DataFrame(results)
    opt_total = float(opt_df["Emisyon (kg CO₂e/yıl)"].sum())
    def component(prefix):
        return float(opt_df.loc[opt_df["Faaliyet"].str.startswith(prefix, na=False), "Emisyon (kg CO₂e/yıl)"].sum())

    # Yalnızca birbirinden bağımsız, hesaplanabilen faaliyetler seçilir.
    options = [
        ("Elektrik tüketimini azaltma", component("Elektrik"), "Elektrik"),
        ("Doğalgaz tüketimini azaltma", component("Doğalgaz"), "Isınma"),
        ("Kömür tüketimini azaltma", component("Kömür"), "Isınma"),
        ("Özel araç yakıtını azaltma", component("Özel araç —"), "Ulaşım"),
        ("Balıkçı teknesi yakıtını azaltma", component("Balıkçı teknesi —"), "Balıkçılık"),
    ]
    eligible = [(name, base, category) for name, base, category in options if base > 0]
    if eligible:
        st.caption("Her senaryo yalnızca ilgili faaliyetin mevcut emisyonunu azaltır. Örneğin özel araç yerine kullanılan toplu taşımanın yeni emisyonu hesaplanmamıştır.")
        scenario_rows = []
        cols = st.columns(2)
        for idx, (name, base, category) in enumerate(eligible):
            with cols[idx % 2]:
                rate = st.slider(f"{name} — varsayımsal azaltım (%)", 0, 100, 20, 5, key=f"opt_rate_{idx}")
            saving = base * rate / 100
            scenario_rows.append({"Senaryo": name, "Kategori": category, "Başlangıç emisyonu": base, "Azaltım (%)": rate, "Potansiyel azaltım": saving, "Senaryo sonrası kısmi toplam": opt_total - saving})

        scen_df = pd.DataFrame(scenario_rows)
        st.markdown("**Tek tek senaryo karşılaştırması**")
        st.dataframe(scen_df, use_container_width=True, hide_index=True, column_config={
            "Başlangıç emisyonu": st.column_config.NumberColumn(format="%.2f kg CO₂e/yıl"),
            "Potansiyel azaltım": st.column_config.NumberColumn(format="%.2f kg CO₂e/yıl"),
            "Senaryo sonrası kısmi toplam": st.column_config.NumberColumn(format="%.2f kg CO₂e/yıl"),
        })
        st.bar_chart(scen_df.set_index("Senaryo")[["Potansiyel azaltım"]])
        total_saving = float(scen_df["Potansiyel azaltım"].sum())
        combined = max(0.0, opt_total - total_saving)
        c1, c2, c3 = st.columns(3)
        c1.metric("Başlangıç kısmi toplamı", f"{opt_total:,.2f} kg CO₂e/yıl")
        c2.metric("Birleşik azaltım potansiyeli", f"{total_saving:,.2f} kg CO₂e/yıl")
        c3.metric("Birleşik senaryo sonrası", f"{combined:,.2f} kg CO₂e/yıl")
        st.caption("Birleşik senaryo, farklı faaliyetlerdeki seçili azaltımları birlikte uygular; her faaliyet yalnızca bir kez hesaba katılır.")

        st.markdown("**Azaltım hedefine ulaşmak için en az kaç senaryo gerekli?**")
        target_pct = st.slider("Kısmi toplam için hedef azaltım (%)", 0, 100, 10, 1, key="opt_target")
        target_kg = opt_total * target_pct / 100
        ranked = sorted(scenario_rows, key=lambda r: r["Potansiyel azaltım"], reverse=True)
        selected, accumulated = [], 0.0
        for row in ranked:
            if accumulated + 1e-9 >= target_kg:
                break
            if row["Potansiyel azaltım"] > 0:
                selected.append(row)
                accumulated += row["Potansiyel azaltım"]
        if target_kg == 0:
            st.success("Hedef %0: herhangi bir senaryo seçilmesi gerekmiyor.")
        elif accumulated + 1e-9 >= target_kg:
            st.success(f"Hedef karşılanabilir: {len(selected)} senaryo ile {accumulated:,.2f} kg CO₂e/yıl potansiyel azaltım (%{100 * accumulated / opt_total:.2f}).")
            st.write("Önerilen senaryolar: " + ", ".join(r["Senaryo"] for r in selected))
        else:
            st.warning(f"Belirlenen azaltım üst sınırlarıyla %{target_pct} hedefi karşılanamıyor. En yüksek birleşik azaltım: {total_saving:,.2f} kg CO₂e/yıl (%{100 * total_saving / opt_total:.2f}).")
        st.caption("**Optimizasyon tanımı:** Kullanıcının verdiği üst sınırlar altında hedefe ulaşmak için *en az sayıda* bağımsız senaryo seçilir. Senaryo maliyetleri, uygulama kolaylığı ve yer değiştirme etkileri bilinmediğinden en düşük maliyetli çözüm iddia edilmez.")
        if missing:
            st.warning("Eksik faaliyetler hesaplamaya alınmadı. Hedef ve yüzdeler yalnızca hesaplanabilen kısmi toplam için geçerlidir.")
    else:
        st.info("Optimizasyon için elektrik, ısınma yakıtı, özel araç veya tekne yakıtında sıfırdan büyük hesaplanmış emisyon bulunmalıdır.")
else:
    st.info("Önce tüketim miktarlarını ve uygun emisyon faktörlerini girin.")

st.caption("Not: Elektrik varsayılanı EVÇED 2023; yakıt varsayılanları DESNZ 2026 Birleşik Krallık doğrudan yanma referanslarıdır. Yakıtın tedarik zinciri emisyonları dahil değildir. Türkiye yakıt bileşimi ve ölçüm yılı farklılıkları sınırlılıktır. Eksik faaliyetler nedeniyle sonuçlar tam karbon ayak izi değildir. Tarımda yalnızca gübre kaynaklı doğrudan N₂O toplam hesabına alınır; züruf için örnek kompost hesabı toplamdan hariçtir ve dolaylı N₂O dahil değildir. Plastik hesabı yalnızca doğrulanmış LDPE/LLDPE ve PET malzemelerinin birincil üretim aşamasını içerir (DESNZ 2025); bertaraf dahil değildir. Gıda modülünde faktör ve yaşam döngüsü kapsamı kullanıcı tarafından kaynaklı girilir; balıkçı teknesi yakıtının gıda yaşam döngüsüyle çakışması ayrıca kontrol edilir. Standart–yerel karşılaştırması yalnızca hesaplanabilen faaliyetlerin kapsam farkını gösterir; duyarlılık analizi yalnızca hesaplanmış faaliyetlerin tek değişkenli ±%10 etkisini gösterir.")
