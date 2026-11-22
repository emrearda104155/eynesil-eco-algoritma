
import json
import pandas as pd
import streamlit as st

from eco_core import (
    DEFAULT, FACTORS, calculate, scenario, pet_scenario,
    biomass_factor, WOOD_NCV, SHELL_NCV
)

st.set_page_config(
    page_title="Eynesil Eco-Algoritma V18",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Eynesil Eco-Algoritma V18")
st.caption(
    "Yıllık kısmi sera gazı emisyonu | "
    "Temel ve genişletilmiş model | "
    "Varsayımsal azaltım senaryoları"
)

st.warning(
    "Bu araç araştırma prototipidir. Katsayılar ve varsayımlar "
    "doğrulanmadan gerçek yerel emisyon ölçümü veya tam karbon "
    "ayak izi olarak yorumlanamaz."
)


def number(label, default=0., step=1., help=None):
    return st.number_input(
        label,
        min_value=0.,
        value=float(default),
        step=float(step),
        help=help
    )


d = DEFAULT.copy()

with st.expander("Katsayılar, kapsam ve bilimsel sınırlılıklar"):
    st.dataframe(
        pd.DataFrame([
            {"Parametre": k, "Değer": v}
            for k, v in FACTORS.items()
        ]),
        hide_index=True
    )

    st.write(
        f"Odun: {biomass_factor(WOOD_NCV):.6f}; "
        f"fındık kabuğu: {biomass_factor(SHELL_NCV):.6f} "
        "kg CO₂e/kg (yalnızca CH₄+N₂O)."
    )

    st.caption(
        "Katsayılar V17 referanslarıdır; kaynak, yıl ve sistem "
        "sınırları bağımsız teyit edilmelidir. Gübre için "
        "50 kg/torba ve %20 azot referans varsayımlarıdır. "
        "Doğrudan toprak N₂O hesabı, gübre üretimini ve "
        "dolaylı emisyonları kapsamaz."
    )


t1, t2, t3, t4 = st.tabs([
    "Enerji ve ısınma",
    "Ulaşım",
    "Plastik",
    "Yerel faaliyetler"
])


with t1:
    d["electric_kwh"] = number(
        "Yıllık elektrik (kWh)", 2400, 100
    )
    d["gas_m3"] = number(
        "Yıllık doğalgaz (m³)", 0, 50
    )
    d["coal_kg"] = number(
        "Yıllık kömür (kg)", 0, 50
    )
    d["wood_kg"] = number(
        "Yıllık odun (kg)", 0, 50
    )
    d["shell_kg"] = number(
        "Yıllık fındık kabuğu (kg)", 0, 50
    )

    st.caption(
        "Elektrikli ısınma toplam elektrik tüketimine "
        "dâhilse ikinci kez girilmez."
    )


with t2:
    d["car_fuel"] = st.selectbox(
        "Özel araç yakıtı",
        ["Benzin", "Dizel", "LPG"]
    )

    method = st.radio(
        "Özel araç miktarı",
        ["Yıllık litre", "Haftalık km ve L/100 km"],
        horizontal=True
    )

    if method == "Yıllık litre":
        d["car_liters"] = number(
            "Yıllık yakıt (L)", 0, 10
        )
    else:
        km = number("Haftalık km", 0, 10)
        rate = number(
            "Araç tüketimi (L/100 km)", 7, 0.5
        )
        d["car_liters"] = km * 52 * rate / 100

    d["bus_passenger_km"] = number(
        "Yıllık minibüs yolcu-km", 0, 100
    )

    d["bus_l100"] = number(
        "Minibüs tüketimi (L/100 km)", 10, 0.5
    )

    d["bus_occupancy"] = st.number_input(
        "Ortalama yolcu sayısı",
        min_value=1.,
        value=8.5,
        step=0.5
    )


with t3:
    bag_week = number(
        "Haftalık yeni poşet (adet)", 4, 1
    )

    d["bag_count"] = bag_week * 52

    d["bag_g"] = number(
        "Bir poşetin kütlesi (g)", 5, 1
    )


with t4:
    st.markdown("**Kıyı balıkçılığı**")

    d["boat_fuel"] = st.selectbox(
        "Tekne yakıtı",
        ["Dizel", "Benzin"]
    )

    d["boat_l_week"] = number(
        "Faaliyet haftasında kullanılan yakıt (L/hafta)",
        0, 5
    )

    d["boat_weeks"] = st.number_input(
        "Yılda faaliyet haftası",
        min_value=0.,
        max_value=52.,
        value=0.,
        step=1.
    )

    st.markdown("**Tarımsal gübre**")

    d["fertilizer_bags"] = number(
        "Yıllık gübre torbası (adet)", 0, 1
    )

    d["fertilizer_bag_kg"] = number(
        "Torba kütlesi (kg)", 50, 5
    )

    d["fertilizer_n_fraction"] = st.number_input(
        "Azot kütle oranı (0–1)",
        min_value=0.,
        max_value=1.,
        value=0.20,
        step=0.01,
        format="%.3f"
    )

    d["fertilizer_ef_n2o"] = st.number_input(
        "Doğrudan N₂O-N emisyon oranı (0–1)",
        min_value=0.,
        max_value=1.,
        value=0.010,
        step=0.001,
        format="%.3f"
    )


r = calculate(d)

st.subheader("Hesaplama sonuçları")

a, b, c, e = st.columns(4)

a.metric(
    "Temel model",
    f"{r['base']:,.2f} kg CO₂e/yıl"
)

b.metric(
    "Genişletilmiş model",
    f"{r['expanded']:,.2f} kg CO₂e/yıl"
)

c.metric(
    "Yerel faaliyet farkı",
    f"{r['local']:,.2f} kg CO₂e/yıl"
)

e.metric(
    "Yerel katkı",
    f"%{r['local_percent']:.2f}"
    if r["local_percent"] is not None
    else "Tanımsız"
)

df = pd.DataFrame([
    {
        "Faaliyet": k,
        "kg CO₂e/yıl": v,
        "Model": "Temel" if i < 6 else "Yerel ek"
    }
    for i, (k, v) in enumerate(r["parts"].items())
])

st.dataframe(
    df.style.format({
        "kg CO₂e/yıl": "{:,.3f}"
    }),
    use_container_width=True,
    hide_index=True
)

st.bar_chart(
    df.set_index("Faaliyet")["kg CO₂e/yıl"]
)


st.subheader("Alternatif azaltım senaryoları")

col1, col2, col3, col4 = st.columns(4)

with col1:
    ep = st.slider(
        "Elektrik azaltımı (%)", 0, 100, 10, 5
    )

with col2:
    cp = st.slider(
        "Özel araç azaltımı (%)", 0, 100, 10, 5
    )

with col3:
    bp = st.slider(
        "Poşet azaltımı (%)", 0, 100, 25, 5
    )

with col4:
    hp = st.slider(
        "Isınma yakıtı azaltımı (%)", 0, 100, 0, 5
    )

s = scenario(
    d,
    electricity=ep,
    car=cp,
    bags=bp,
    heating=hp
)

x, y, z = st.columns(3)

x.metric(
    "Senaryo toplamı",
    f"{s['alternative']:,.2f} kg CO₂e/yıl"
)

y.metric(
    "Tahmini fark",
    f"{s['difference']:,.2f} kg CO₂e/yıl"
)

z.metric(
    "Tahmini azalma",
    f"%{s['percent']:.2f}"
    if s["percent"] is not None
    else "Tanımsız"
)

st.caption(
    "Senaryo, diğer faaliyetlerin sabit kaldığı varsayımsal "
    "karşılaştırmadır; gerçekleşmiş azaltım değildir. "
    "Özel araçtan toplu taşımaya geçişin ilave etkisi "
    "bu sürümde modellenmemiştir."
)


st.markdown(
    "#### PET geri dönüşümü (ana toplamdan bağımsız)"
)

pet_count = number(
    "Ayda geri dönüşüme gönderilen PET şişe (adet)",
    0, 1
)

pet_g = number(
    "PET şişe kütlesi (g)", 20, 1
)

pet = pet_scenario(pet_count, pet_g)

st.metric(
    "EPA WARM varsayımına göre tahmini fark",
    f"{pet:,.3f} kg CO₂e/yıl"
)

st.caption(
    "ABD EPA WARM v16 geri dönüşüm–düzenli depolama "
    "referansı; Türkiye için doğrulanmış tasarruf değildir."
)


result = {
    "model": "Eco-Algoritma V18",
    "kapsam": "Yıllık kısmi emisyon",
    "girdiler": d,
    "katsayilar": FACTORS,
    "bilesenler": r["parts"],
    "temel_kg_co2e_yil": r["base"],
    "genisletilmis_kg_co2e_yil": r["expanded"],
    "yerel_fark_kg_co2e_yil": r["local"],
    "yerel_katki_yuzde": r["local_percent"],
    "senaryo": s,
    "pet_ayri_senaryo_kg": pet
}

st.download_button(
    "📥 Bulgular JSON",
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ),
    "eco_v18_sonuc.json",
    "application/json"
)

st.download_button(
    "📊 Bileşen CSV",
    df.to_csv(index=False).encode("utf-8-sig"),
    "eco_v18_bilesenler.csv",
    "text/csv"
)

st.markdown(
    "**Kaynak bağlantıları:** "
    "[IPCC 2006](https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html) · "
    "[IPCC 2019](https://www.ipcc-nggip.iges.or.jp/public/2019rf/index.html) · "
    "[EPA WARM](https://www.epa.gov/warm) · "
    "[Fındık kabuğu çalışması](https://www.mdpi.com/1996-1073/16/3/1297)"
)
