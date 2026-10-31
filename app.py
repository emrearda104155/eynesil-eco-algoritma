"""Eynesil Eco-Algoritma V17 — raporla uyumlu, üç modüllü prototip.
Kurulum: pip install streamlit pandas
Çalıştırma: streamlit run Eco_Algoritma_Yeni_Model_V17.py
Katsayılar literatür/referans temelli tahminlerdir, yerel ölçüm değildir.
"""
import json
import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Eynesil Eco-Algoritma', page_icon='🌿', layout='centered')
st.title('🌿 Eynesil Eco-Algoritma')
st.caption('Enerji • Ulaşım • Plastik | Yıllık kısmi emisyon hesabı ve alternatif senaryolar')

# Eski V16 referansları; farklı sistem sınırları ve güncel yıl uyumu raporda açıklanmalıdır.
FACTORS = {'Elektrik (kg CO₂e/kWh)': 0.469,
           'Doğalgaz (kg CO₂e/m³)': 2.02633,
           'Kömür (kg CO₂e/kg)': 2.90495,
           'Benzin (kg CO₂e/L)': 2.075,
           'Dizel (kg CO₂e/L)': 2.58354,
           'LPG (kg CO₂e/L)': 1.55713,
           'Poşet / LDPE (kg CO₂e/kg)': 2.96508}
# IPCC 2006, konut biyokütle yakımı: CH4 300 kg/TJ; N2O 4 kg/TJ.
# GWP100: AR5 CH4=28 ve N2O=265; tek sürüm boyunca tutarlı kullanılır.
BIO_CH4, BIO_N2O, GWP_CH4, GWP_N2O = 300.0, 4.0, 28.0, 265.0
WOOD_NCV, SHELL_NCV = 15.6, 19.10  # MJ/kg; kabuk literatürde iki örneğin ortalaması
ROUTES = {'Eynesil–Giresun': (73.0, 7.0), 'Eynesil–Trabzon': (59.0, 5.5)}
PET_WARM_RECYCLING, PET_WARM_LANDFILL = -1.04, 0.02  # MT CO2e/US short ton


def biomass_factor(ncv):
    return ncv * (BIO_CH4 * GWP_CH4 + BIO_N2O * GWP_N2O) / 1_000_000


def compute(data, factors=FACTORS):
    """Girdi birimleri açık; negatif/sonsuz girdiler reddedilir."""
    if any(not math.isfinite(float(v)) or float(v) < 0 for v in data.values()):
        raise ValueError('Tüm girdiler sıfır veya pozitif sonlu sayı olmalıdır.')
    return {
        'Elektrik': data['electric_kwh'] * factors['Elektrik (kg CO₂e/kWh)'],
        'Doğalgaz': data['gas_m3'] * factors['Doğalgaz (kg CO₂e/m³)'],
        'Kömür': data['coal_kg'] * factors['Kömür (kg CO₂e/kg)'],
        'Odun (CH₄+N₂O)': data['wood_kg'] * biomass_factor(WOOD_NCV),
        'Fındık kabuğu (CH₄+N₂O)': data['shell_kg'] * biomass_factor(SHELL_NCV),
        'Özel araç': data['car_liters'] * factors[f"{data['car_fuel']} (kg CO₂e/L)"],
        'Minibüs (kişi payı)': data['bus_passenger_km'] * data['bus_l_per_100km'] / 100 / data['bus_occupancy'] * factors['Dizel (kg CO₂e/L)'],
        'Plastik poşet (malzeme)': data['bag_count'] * data['bag_g'] / 1000 * factors['Poşet / LDPE (kg CO₂e/kg)']
    }


def n(label, value=0.0, step=1.0, key=None, help=None):
    return st.number_input(label, min_value=0.0, value=float(value), step=float(step), key=key, help=help)

with st.expander('🔬 Kullanılan referans katsayılar ve sınırlar'):
    st.dataframe(pd.DataFrame([{'Katsayı': k, 'Değer': v} for k, v in FACTORS.items()]), hide_index=True)
    st.write(f'Odun: **{biomass_factor(WOOD_NCV):.6f} kg CO₂e/kg**; fındık kabuğu: **{biomass_factor(SHELL_NCV):.6f} kg CO₂e/kg** (yalnızca CH₄ ve N₂O).')
    st.caption('Biyojenik CO₂, yakıt tedariki ve arazi kullanımı etkileri bu iki katsayıya dahil değildir. Fındık kabuğu 19,10 MJ/kg değeri yerel ölçüm değil, yayın örneklerinin ortalamasıdır.')
    st.caption('Elektrik 0,469 ve fosil yakıt katsayıları önceki V16 sürümünden alınmıştır; proje raporunda referans yılı ve birimleri teyit edilmelidir.')

st.subheader('1. Enerji ve ısınma')
a, b = st.columns(2)
with a:
    electric = n('Yıllık elektrik (kWh)', 2400, 100)
    gas = n('Yıllık doğalgaz (m³)', 0, 50)
    coal = n('Yıllık kömür (kg)', 0, 50)
with b:
    wood = n('Yıllık odun (kg)', 0, 50)
    shell = n('Yıllık fındık kabuğu (kg)', 0, 50)
st.caption('Elektrikli ısınma toplam elektrik tüketimine dahilse tekrar girilmez. Odun ve fındık kabuğu, fındık zürufundan farklıdır.')

st.subheader('2. Ulaşım')
car_fuel = st.selectbox('Özel araç yakıtı', ['Benzin', 'Dizel', 'LPG'])
car_method = st.radio('Özel araç tüketimi', ['Yıllık litre', 'Haftalık km ve L/100 km'], horizontal=True)
if car_method == 'Yıllık litre':
    car_liters = n('Yıllık özel araç yakıtı (L)', 0, 20)
else:
    weekly_km = n('Haftalık özel araç mesafesi (km)', 0, 10)
    car_rate = n('Özel araç tüketimi (L/100 km)', 7, 0.5)
    car_liters = weekly_km * 52 * car_rate / 100
bus_mode = st.selectbox('Minibüs kullanımı', ['Kullanmıyorum', 'Eynesil–Giresun', 'Eynesil–Trabzon', 'Diğer güzergâh'])
bus_pkm, bus_l100, bus_occupancy = 0.0, 0.0, 1.0
if bus_mode != 'Kullanmıyorum':
    if bus_mode in ROUTES:
        route_km, liters_oneway = ROUTES[bus_mode]
        bus_l100 = liters_oneway / route_km * 100
        st.caption(f'Önceki V16 saha varsayımı: {route_km:g} km/tek yön; {liters_oneway:g} L/tek yön. Doğrulanmış ölçüm değildir.')
        trips = n('Haftalık tek yön yolculuk sayısı (gidiş ve dönüş ayrı sayılır)', 2, 1)
        bus_pkm = trips * 52 * route_km
    else:
        bus_pkm = n('Yıllık yolcu-km', 0, 100)
        bus_l100 = n('Minibüs yakıt tüketimi (L/100 km)', 10, 0.5)
    bus_occupancy = st.number_input('Ortalama yolcu sayısı (varsayım)', min_value=1.0, value=8.5, step=0.5)

st.subheader('3. Plastik tüketimi')
bag_week = n('Haftalık plastik poşet (adet)', 4, 1)
bag_g = n('Bir poşetin kütlesi (g)', 5, 1)

st.divider()
data = dict(electric_kwh=electric, gas_m3=gas, coal_kg=coal, wood_kg=wood,
            shell_kg=shell, car_liters=car_liters, car_fuel=car_fuel,
            bus_passenger_km=bus_pkm, bus_l_per_100km=bus_l100,
            bus_occupancy=bus_occupancy, bag_count=bag_week * 52, bag_g=bag_g)
parts = compute(data)
energy_keys = ['Elektrik', 'Doğalgaz', 'Kömür', 'Odun (CH₄+N₂O)', 'Fındık kabuğu (CH₄+N₂O)']
transport_keys = ['Özel araç', 'Minibüs (kişi payı)']
plastic_keys = ['Plastik poşet (malzeme)']
base_energy = sum(parts[k] for k in energy_keys)
base_transport = sum(parts[k] for k in transport_keys)
base_plastic = sum(parts[k] for k in plastic_keys)
base_total = base_energy + base_transport + base_plastic
st.subheader('Hesaplama sonuçları')
st.metric('Yıllık hesaplanan kısmi emisyon', f'{base_total:,.2f} kg CO₂e')
summary = pd.DataFrame([{'Modül': 'Enerji', 'kg CO₂e/yıl': base_energy},
                        {'Modül': 'Ulaşım', 'kg CO₂e/yıl': base_transport},
                        {'Modül': 'Plastik', 'kg CO₂e/yıl': base_plastic}])
st.dataframe(summary.style.format({'kg CO₂e/yıl': '{:,.2f}'}), hide_index=True, use_container_width=True)
st.caption('Bu toplam tam yaşam döngüsü karbon ayak izi değildir. Farklı sınırları olan referans faktörlerle hesaplanan kısmi bir göstergedir.')

st.subheader('H1 — Standart ve yerel kapsam karşılaştırması')
standard_energy = sum(parts[k] for k in ['Elektrik', 'Doğalgaz', 'Kömür'])
local_energy = base_energy
st.dataframe(pd.DataFrame([
    {'Model': 'Standart enerji kapsamı (elektrik + fosil)', 'kg CO₂e/yıl': round(standard_energy, 3)},
    {'Model': 'Genişletilmiş yerel enerji kapsamı (+ odun + fındık kabuğu)', 'kg CO₂e/yıl': round(local_energy, 3)}
]), hide_index=True, use_container_width=True)
st.caption(f'Eklenen biyokütle bileşeni: {local_energy-standard_energy:,.2f} kg CO₂e/yıl. Bu bir yerel emisyon katsayısı ölçümü veya emisyon azaltımı değildir; faaliyet kapsamı farkıdır.')

st.subheader('H2 — Alternatif azaltım senaryosu')
electric_pct = st.slider('Elektrik tüketiminde azalma (%)', 0, 50, 10, 5)
heat_pct = st.slider('Isınma yakıtlarının tüketiminde azalma (%)', 0, 50, 10, 5)
car_pct = st.slider('Özel araç kullanımında azalma (%)', 0, 50, 10, 5)
bag_pct = st.slider('Plastik poşet kullanımında azalma (%)', 0, 100, 25, 5)
replacement_mode = st.selectbox('Azaltılan özel araç yolculuğu', ['Yapılmayacak', 'Minibüsle yapılacak'])
replacement = 0.0
valid_replacement = True
if replacement_mode == 'Minibüsle yapılacak' and car_pct > 0 and car_liters > 0:
    shifted_km = None
    if car_method == 'Haftalık km ve L/100 km':
        shifted_km = weekly_km * 52 * car_pct / 100
    if shifted_km is None:
        st.warning('Minibüse geçiş hesabı için özel araç tüketimini “Haftalık km ve L/100 km” biçiminde girin.')
        valid_replacement = False
    else:
        alt_l100 = n('Alternatif minibüs tüketimi (L/100 km)', 10, 0.5)
        alt_occupancy = st.number_input('Alternatif minibüs ortalama yolcu sayısı', min_value=1.0, value=8.5, step=0.5)
        replacement = shifted_km * alt_l100 / 100 / alt_occupancy * FACTORS['Dizel (kg CO₂e/L)']
heat_other = base_energy - parts['Elektrik']
scenario_total = (parts['Elektrik'] * (1-electric_pct/100) + heat_other * (1-heat_pct/100)
                  + parts['Özel araç'] * (1-car_pct/100) + parts['Minibüs (kişi payı)']
                  + replacement + base_plastic * (1-bag_pct/100))
if valid_replacement:
    c1, c2, c3 = st.columns(3)
    c1.metric('Mevcut', f'{base_total:,.1f} kg')
    c2.metric('Senaryo', f'{scenario_total:,.1f} kg')
    c3.metric('Net fark', f'{base_total-scenario_total:,.1f} kg')
    st.caption(f'Göreli değişim: %{(base_total-scenario_total)/base_total*100 if base_total else 0:.1f}. Varsayımsal senaryodur, gerçekleşmiş azaltım değildir.')

st.markdown('#### PET geri dönüşümü — ayrı senaryo')
pet_month = n('Ayda geri dönüşüme yönlendirilen PET şişe (adet)', 0, 1)
pet_g = n('Bir PET şişe kütlesi (g)', 20, 1)
pet_annual_kg = pet_month * 12 * pet_g / 1000
pet_avoided = pet_annual_kg / 907.18474 * (PET_WARM_LANDFILL-PET_WARM_RECYCLING) * 1000
st.metric('PET için varsayımsal yıllık kaçınılan emisyon', f'{pet_avoided:,.2f} kg CO₂e')
st.caption('EPA WARM v16 ABD geri dönüşüm–düzenli depolama karşılaştırmasıdır; Türkiye için doğrulanmış tasarruf değildir. Ana toplamdan düşülmez.')

st.markdown('#### Bulgular için dışa aktarım')
result = {'kapsam': 'Yıllık kısmi emisyon; 3 modül', 'girdiler': data, 'bilesenler_kg_co2e_yil': parts,
          'moduller_kg_co2e_yil': {'enerji': base_energy, 'ulasim': base_transport, 'plastik': base_plastic},
          'temel_toplam_kg_co2e_yil': base_total,
          'h1_standart_enerji_kg': standard_energy, 'h1_genisletilmis_enerji_kg': local_energy,
          'h2_senaryo_kg': scenario_total if valid_replacement else None,
          'h2_fark_kg': base_total-scenario_total if valid_replacement else None,
          'pet_ayri_senaryo_kg': pet_avoided}
st.download_button('📥 Sonuçları JSON indir', json.dumps(result, ensure_ascii=False, indent=2), 'eynesil_sonuc.json', 'application/json')
st.download_button('📊 Bileşen tablosunu CSV indir', pd.DataFrame([{'Faaliyet': k, 'kg CO₂e/yıl': v} for k,v in parts.items()]).to_csv(index=False).encode('utf-8-sig'), 'eynesil_bilesenler.csv', 'text/csv')
with st.expander('📚 Bilimsel kaynaklar ve metodolojik notlar'):
    st.write('IPCC 2006 Vol. 2, Ch. 1–2: https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html')
    st.write('Fındık kabuğu alt ısıl değeri: Energies (2023), 16(3), 1297: https://www.mdpi.com/1996-1073/16/3/1297')
    st.write('EPA WARM: https://www.epa.gov/warm')
    st.caption('GWP100 AR5: CH₄=28, N₂O=265. Eski V16 AR6 değerleriyle karıştırılmamıştır. Sabit yakıt faktörlerinin rapordaki referanslarla teyidi gereklidir.')
