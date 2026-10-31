"""Eco-Algoritma V16 | Proje hipotezlerine bağlı hesaplama revizyonu.
Run: pip install streamlit pandas gspread google-auth
     streamlit run eco_algoritma.py
Optional private Google Sheets: .streamlit/secrets.toml [connections.gsheets] spreadsheet_id = ...
[connections.gsheets.service_account] ... Google service account JSON fields.
Only pseudonymous responses are collected after explicit consent. No names/IP requested.
"""
import csv
import io
import json
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

# Dahili hesaplama modulleri: harici eco_vXX dosyalarina bagimlilik yok.
"""Eco-Algoritma V12: ölçülebilir senaryo ve yerel minibüs belirsizliği."""
F_DIESEL=2.58354
ROUTES={'Eynesil–Giresun':(73.0,6.5,7.0,7.5),'Eynesil–Trabzon':(59.0,5.0,5.5,6.0)}

def minibus_range(route, weekly_trips, roundtrip=True, weeks=52):
    if route not in ROUTES: raise ValueError('Bilinmeyen hat')
    if weekly_trips<0: raise ValueError('Negatif sefer')
    km, low,mid,high=ROUTES[route]
    trips=weekly_trips*(2 if roundtrip else 1)*weeks
    return {'km_year':km*trips,'low':trips*low/9*F_DIESEL,
            'central':trips*mid/8.5*F_DIESEL,'high':trips*high/8*F_DIESEL}

def scenario(base, changes):
    """changes: {faaliyet: (azaltma_orani_0_1, alternatif_emisyon_kg)}.
    Net savings include replacement-mode emissions; no claim of realized reduction.
    """
    if any(v<0 for v in base.values()): raise ValueError('Negatif temel emisyon')
    original=sum(base.values()); new=dict(base)
    for key,(reduction,alternative) in changes.items():
        if key not in base or not 0<=reduction<=1 or alternative<0:raise ValueError('Geçersiz senaryo')
        new[key]=base[key]*(1-reduction)+alternative
    updated=sum(new.values());saved=original-updated
    return {'baseline':original,'alternative':updated,'difference':saved,
            'percent':100*saved/original if original else 0}

"""Eco-Algoritma V14: IPCC biyokütle, karşılaştırma, duyarlılık ve senaryolar.
Birimler açıkça belirtilir; fındık kabuğu için odun ısıl değeri yalnızca vekil senaryodur.
"""
GWP_CH4=27.2
GWP_N2O=273.0
# IPCC 2006 Vol 2 Chapter 2 Table 2.5 residential: wood/wood waste and other primary solid biomass
CH4_KG_TJ=300.0
N2O_KG_TJ=4.0
WOOD_NCV_MJ_KG=15.6  # IPCC 2006 Vol 2 Chapter 1, air dry wood/wood waste
WOOD_BIOGENIC_CO2_KG_TJ=112000.0
SHELL_BIOGENIC_CO2_KG_TJ=100000.0 # Other primary solid biomass; not hazelnut-specific

def biomass_emissions(kg, ncv_mj_kg=WOOD_NCV_MJ_KG, category='wood'):
    if kg < 0 or ncv_mj_kg <= 0 or category not in ('wood','shell'):
        raise ValueError('Geçersiz biyokütle girdisi')
    tj=kg*ncv_mj_kg/1_000_000
    ch4=tj*CH4_KG_TJ
    n2o=tj*N2O_KG_TJ
    return {'non_co2_kg_co2e':ch4*GWP_CH4+n2o*GWP_N2O,
            'ch4_kg':ch4,'n2o_kg':n2o,
            'biogenic_co2_kg_memo':tj*(WOOD_BIOGENIC_CO2_KG_TJ if category=='wood' else SHELL_BIOGENIC_CO2_KG_TJ),
            'energy_tj':tj}

def comparable_minibus(route, weekly_trips, standard_kg_per_passenger_km, roundtrip=True):
    """Same passenger-km, standard published factor versus local fuel/occupancy assumptions."""
    if standard_kg_per_passenger_km is None or standard_kg_per_passenger_km <= 0:
        raise ValueError('Standart yolcu-km faktörü kaynaklandırılmalı')
    local=minibus_range(route,weekly_trips,roundtrip)
    return {'standard_kg':local['km_year']*standard_kg_per_passenger_km,
            'local_kg':local['central'], 'difference_kg':local['central']-local['km_year']*standard_kg_per_passenger_km,
            'passenger_km':local['km_year']}

def modal_shift(car_baseline_kg, displaced_fraction, replacement_kg):
    if not 0<=displaced_fraction<=1 or min(car_baseline_kg,replacement_kg)<0:
        raise ValueError('Geçersiz değişken')
    alternative=car_baseline_kg*(1-displaced_fraction)+replacement_kg
    return {'baseline':car_baseline_kg,'alternative':alternative,
            'difference':car_baseline_kg-alternative,
            'percent':(car_baseline_kg-alternative)/car_baseline_kg*100 if car_baseline_kg else 0}

"""V15: Proje raporuna bağlı H1/H2/H3 araştırma hesapları.
Bilinmeyen katsayılar için sayı üretmez; farklı sistem sınırları ayrı tutulur.
"""
from math import isfinite

def positive_or_zero(value, name):
    if value is None or not isfinite(float(value)) or float(value) < 0:
        raise ValueError(f'{name}: sıfır veya pozitif sonlu sayı gerekli')
    return float(value)

def fertilizer_n_kg(bags, bag_kg, nitrogen_pct):
    for name, val in [('Torba',bags),('Torba kütlesi',bag_kg),('N oranı',nitrogen_pct)]: positive_or_zero(val,name)
    if nitrogen_pct>100: raise ValueError('Azot oranı %100 üstünde olamaz')
    return bags*bag_kg*nitrogen_pct/100

def fertilizer_direct_kg_co2e(n_kg, ef1=0.01, gwp_n2o=273):
    for name, val in [('Azot',n_kg),('EF1',ef1),('GWP',gwp_n2o)]:positive_or_zero(val,name)
    return n_kg*ef1*(44/28)*gwp_n2o

def fertilizer_indirect_kg_co2e(n_kg, frac_gas, ef4, frac_leach, ef5, gwp_n2o=273):
    """IPCC 2019 genel akış şeması; parametreler kaynaklandırılmadan hesaplanmaz."""
    for name,val in [('Azot',n_kg),('FracGASF',frac_gas),('EF4',ef4),('FracLEACH',frac_leach),('EF5',ef5),('GWP',gwp_n2o)]:positive_or_zero(val,name)
    if frac_gas>1 or frac_leach>1:raise ValueError('Fraksiyon 0-1 aralığında olmalı')
    return n_kg*(frac_gas*ef4+frac_leach*ef5)*(44/28)*gwp_n2o

def boat_emissions(weekly_liters, kg_per_liter, allocation='tam', people=None):
    """Teknenin tüm yakıtı veya kişi payı; ikisi birlikte asla toplanmaz."""
    positive_or_zero(weekly_liters,'Haftalık litre');positive_or_zero(kg_per_liter,'Faktör')
    annual=weekly_liters*52*kg_per_liter
    if allocation=='tam':return annual
    if allocation=='kisi':
        if people is None or people<1 or int(people)!=people:raise ValueError('Geçerli kişi sayısı gerekli')
        return annual/people
    raise ValueError('Tahsis yöntemi bilinmiyor')

def food_emissions(weekly_kg, factor=None, source=None):
    positive_or_zero(weekly_kg,'Haftalık gıda miktarı')
    if factor is None or not source or not str(source).strip():return None
    positive_or_zero(factor,'Gıda faktörü')
    return weekly_kg*52*factor

def paired_comparison(standard, local):
    """Aynı birim ve aynı faaliyet sınırı sağlanmış iki yıllık değer."""
    positive_or_zero(standard,'Standart');positive_or_zero(local,'Yerel')
    return {'standard':standard,'local':local,'difference':local-standard,'difference_pct':(local-standard)/standard*100 if standard else None}


def boat_annual_emissions(weekly_liters, active_weeks, kg_per_liter, allocation='tam', people=None):
    """Aktif haftalar üzerinden yıllık tekne yakıtı; 52 hafta varsayılmaz."""
    positive_or_zero(weekly_liters,'Aktif haftalık yakıt')
    positive_or_zero(active_weeks,'Aktif hafta')
    positive_or_zero(kg_per_liter,'Yakıt faktörü')
    if active_weeks > 52:raise ValueError('Yıllık aktif hafta 52 üstünde olamaz')
    total=weekly_liters*active_weeks*kg_per_liter
    if allocation=='tam':return total
    if allocation=='kisi':
        if people is None or people<1 or int(people)!=people:raise ValueError('Kişi sayısı geçersiz')
        return total/people
    raise ValueError('Paylaştırma yöntemi geçersiz')

def integrated_scenario(base, electric_fraction=0, car_fraction=0, replacement_kg=0):
    """Tek seferlik elektrik/araç azaltımı ve varsa yeni toplu taşıma emisyonu."""
    for name,v in base.items():positive_or_zero(v,name)
    for name,f in [('Elektrik azaltımı',electric_fraction),('Araç azaltımı',car_fraction)]:
        positive_or_zero(f,name)
        if f>1:raise ValueError('Azaltım 0-1 arasında olmalı')
    positive_or_zero(replacement_kg,'Yeni ulaşım emisyonu')
    baseline=sum(base.values())
    alternative=baseline-base.get('Elektrik',0)*electric_fraction-base.get('Özel araç',0)*car_fraction+replacement_kg
    return {'baseline':baseline,'alternative':alternative,'difference':baseline-alternative,'percent':100*(baseline-alternative)/baseline if baseline else 0}

st.set_page_config(page_title="Eynesil Karbon Rehberim", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container {max-width:700px;padding:1rem .85rem 5rem}
h1 {font-size:1.75rem!important;line-height:1.18!important}
h2,h3 {font-size:1.18rem!important}
div.stButton>button {min-height:3.2rem;border-radius:14px;font-size:1.03rem;font-weight:650}
div[data-testid="stMetric"] {background:#f0f8f1;padding:14px;border-radius:16px}
@media(max-width:600px){.block-container{padding:.7rem .6rem 5rem}div[data-testid="stHorizontalBlock"]{gap:.4rem}}
.hero{background:linear-gradient(125deg,#e8f5e9,#f5faf5);border-radius:18px;padding:18px;margin:10px 0 14px;color:#183f28}
.mini{font-size:.89rem;color:#506358}.pill{display:inline-block;background:#d8eddd;color:#215b33;border-radius:20px;padding:5px 12px;font-weight:600}
</style>""", unsafe_allow_html=True)

# Kullanıcı beyanı; henüz ölçümle doğrulanmamış saha varsayımları.
ROUTES = {'Eynesil–Giresun': {'km':73.0,'liters_trip':7.0,'range':(6.5,7.5)}, 'Eynesil–Trabzon': {'km':59.0,'liters_trip':5.5,'range':(5.0,6.0)}}
LOCAL = {'minibus_passengers_low':8, 'minibus_passengers_high':9, 'minibus_passengers_mean':8.5, 'trips_per_route_reported':6, 'yayla_elevation_m_approx':2000, 'yayla_visits_per_month':1, 'yayla_fuel_uplift_reported':0.20}
F = {"elektrik":0.469,"gaz":2.02633,"komur":2.90495,"Benzin":2.075,"Dizel":2.58354,"LPG":1.55713,"LDPE":2.96508,"PET":3.86390,"beef":99.48}
# EPA WARM v16 (2023), geri dönüşüm yerine düzenli depolama karşılaştırması.
# Değerler ABD referans senaryosudur; Türkiye/DOA için ölçülmüş katsayı değildir.
# 1 ABD short ton = 907.18474 kg. Birimler: MT CO2e / short ton.
DOA_WARM = {
    "PET": {"recycling": -1.04, "landfill": 0.02, "default_g": 20.0},
    "Cam": {"recycling": -0.28, "landfill": 0.02, "default_g": 250.0},
}

def doa_scenario(pet_count, glass_count, pet_g=20.0, glass_g=250.0, periods_per_year=12):
    """Ayrı bir geri dönüşüm karşılaştırma senaryosu; ana ayak izinden düşülmez."""
    if any(x < 0 for x in (pet_count, glass_count, pet_g, glass_g, periods_per_year)):
        raise ValueError("Negatif miktar olamaz")
    details = {}
    for name, count, mass_g in (("PET", pet_count, pet_g), ("Cam", glass_count, glass_g)):
        annual_kg = count * mass_g / 1000 * periods_per_year
        avoided = annual_kg / 907.18474 * (DOA_WARM[name]["landfill"] - DOA_WARM[name]["recycling"]) * 1000
        details[name] = {"annual_kg": annual_kg, "potential_kg_co2e": avoided}
    return details

STEPS=["Başlangıç","Ev ve enerji","Ulaşım","Tarım ve yerel yaşam","Günlük tüketim","Sonuçlar"]
if "step" not in st.session_state: st.session_state.step=0
if "sid" not in st.session_state: st.session_state.sid=str(uuid.uuid4())
if "submitted" not in st.session_state: st.session_state.submitted=False

def select(k,q,opts,help=None):
    return st.selectbox(q,opts,key=k,help=help)
def num(k,q,step=1.0):
    return st.number_input(q,min_value=0.0,step=float(step),value=None,placeholder="Bilmiyorsanız boş bırakın",key=k)
def line(title,body):
    st.markdown(f"**{title}**")
    st.caption(body)
def annualize(x,frequency):
    if x is None:return None
    return x*({"hafta":52,"ay":12,"yıl":1}[frequency])

def calculate():
    v=st.session_state; rows=[]; missing=[]
    def add(label,category,activity,ef):
        if activity is None: missing.append(label);return
        rows.append({"Faaliyet":label,"Modül":category,"kg CO₂e/yıl":round(activity*ef,3)})
    if v.get('electric_use')=='Evet':
        if v.get('electric_mode')=='Mevsime göre ayrı':
            winter=v.get('elec_winter');summer=v.get('elec_other');months=v.get('winter_months',4)
            annual_elec=(winter*months+summer*(12-months)) if winter is not None and summer is not None else None
        else: annual_elec=annualize(v.get('electric'),'ay')
        add('Elektrik','Enerji',annual_elec,F['elektrik'])
    if 'Doğalgaz' in v.get('heating_sources', []):
        if v.get('gas_mode')=='Mevsime göre ayrı':
            winter=v.get('gas_winter');summer=v.get('gas_other');months=v.get('winter_months',4)
            annual_gas=(winter*months+summer*(12-months)) if winter is not None and summer is not None else None
        else: annual_gas=annualize(v.get('gas'),'ay')
        add('Doğalgaz','Enerji',annual_gas,F['gaz'])
    if 'Kömür' in v.get('heating_sources', []):add('Kömür','Enerji',v.get('coal'),F['komur'])
    if 'Odun' in v.get('heating_sources', []):
        amount=v.get('wood_kg')
        if amount is None:missing.append('Odun miktarı (kg)')
        else:
            bio=biomass_emissions(amount,category='wood')
            rows.append({'Faaliyet':'Odun yakımı CH₄+N₂O (biyojenik CO₂ hariç)','Modül':'Enerji','kg CO₂e/yıl':round(bio['non_co2_kg_co2e'],3)})
            rows.append({'Faaliyet':'Odun biyojenik CO₂ (bilgi amaçlı, toplam dışı)','Modül':'Biyojenik CO₂ (ayrı)','kg CO₂e/yıl':round(bio['biogenic_co2_kg_memo'],3)})
    if 'Fındık kabuğu' in v.get('heating_sources', []):
        amount=v.get('shell_kg'); ncv=v.get('shell_ncv',15.6)
        if amount is None:missing.append('Fındık kabuğu miktarı (kg)')
        else:
            bio=biomass_emissions(amount,ncv_mj_kg=ncv,category='shell')
            rows.append({'Faaliyet':'Fındık kabuğu CH₄+N₂O (genel biyokütle vekil)','Modül':'Enerji','kg CO₂e/yıl':round(bio['non_co2_kg_co2e'],3)})
            rows.append({'Faaliyet':'Fındık kabuğu biyojenik CO₂ (bilgi amaçlı)','Modül':'Biyojenik CO₂ (ayrı)','kg CO₂e/yıl':round(bio['biogenic_co2_kg_memo'],3)})
            missing.append('Fındık kabuğu için yerel alt ısıl değer ve soba emisyon ölçümü yapılmadı; odun NCV vekil kullanıldı')
    if 'Diğer / bilmiyorum' in v.get('heating_sources', []):missing.append('Diğer ısınma yakıtı: uygun faktör eksik')
    if v.get('car')=='Evet':
        fuel=v.get('fuel')
        if fuel in ('Benzin','Dizel','LPG'):
            if v.get('car_input')=='Haftalık yakıt (litre)':a=annualize(v.get('car_liters'),'hafta')
            elif v.get('car_input')=='Haftalık yol (km)':
                km=v.get('car_km');rate=v.get('car_rate');a=km*52*rate/100 if km is not None and rate is not None else None
            else:a=None
            add('Özel araç','Ulaşım',a,F[fuel])
        else:missing.append('Özel araç enerji tüketimi')
    # commute_mode is survey metadata; its trips are included in car_km / bus_trips_week.
    if v.get('farm')=='Evet' and v.get('fert')=='Evet':
        b=v.get('bags');m=v.get('bag_weight');p=v.get('n_percent')
        nitrogen=fertilizer_n_kg(b,m,p) if all(x is not None for x in (b,m,p)) else None
        add('Gübre: doğrudan N₂O','Tarım',nitrogen,0.010*(44/28)*273)
        missing.append('Gübrenin dolaylı N₂O ve üretim emisyonları (kaynaklandırılmış parametre gerektirir)')
    # Züruf yakılmıyorsa açıkta yakma emisyonu hesaplanmaz; diğer işlemler ayrı kapsamdır.
    if v.get('boat')=='Evet':
        fuel=v.get('boat_fuel')
        if fuel in ('Benzin','Dizel'):
            liters=v.get('boat_liters')
            if liters is None:missing.append('Balıkçı teknesi yakıt miktarı')
            else:
                allocation='kisi' if v.get('boat_allocation')=='Kişi başına eşit pay' else 'tam'
                crew=v.get('boat_people') if allocation=='kisi' else None
                if allocation=='kisi' and crew is None:missing.append('Tekne kişi payı için kişi sayısı')
                else:rows.append({'Faaliyet':'Balıkçı teknesi' + (' (kişi payı)' if allocation=='kisi' else ' (tam yakıt)'),'Modül':'Yerel faaliyet','kg CO₂e/yıl':round(boat_annual_emissions(liters,v.get('boat_active_weeks'),F[fuel],allocation,crew),3)}) if v.get('boat_active_weeks') is not None else missing.append('Balıkçılıkta yıllık aktif hafta sayısı')
        else:missing.append('Tekne yakıtı')
    if v.get('plastic')=='Evet':
        for label,count_key,weight_key,ef in [('Poşet malzemesi','bags_week','bag_g',F['LDPE']),('PET şişe gövdesi','bottles_week','bottle_g',F['PET'])]:
            count=v.get(count_key);weight=v.get(weight_key)
            add(label,'Plastik malzeme',count*52*weight/1000 if count is not None and weight is not None else None,ef)
        missing.append('Plastik atıkların toplanması ve bertarafı (malzeme üretimi hesabı dışında)')
    if v.get('bus')=='Evet':
        km=v.get('bus_km')
        route=v.get('bus_route')
        if route in ROUTES and v.get('bus_trips_week') is not None:
            direction=v.get('bus_trip_type','Gidiş-dönüş')
            km=ROUTES[route]['km']*v['bus_trips_week']*(2 if direction=='Gidiş-dönüş' else 1)
        liters_100=(100*ROUTES[route]['liters_trip']/ROUTES[route]['km'] if route in ROUTES else v.get('local_minibus_l100'))
        occupancy=LOCAL['minibus_passengers_mean']
        if km is not None and liters_100 is not None and occupancy>0:
            add('Minibüs (kişi payı)','Ulaşım',km*52*liters_100/(100*occupancy),F['Dizel'])
        else:
            missing.append('Minibüs: güzergâh ve yakıt tüketimi verisi gerekli')
    if v.get('food')=='Evet':
        meat=v.get('beef_kg')
        add('Sığır eti (küresel yaşam döngüsü ortalaması)','Beslenme',annualize(meat,'hafta'),F['beef'])
        missing.append('Diğer gıda türleri: doğrulanmış yaşam döngüsü faktörü olmadan toplam dışı')
        for food_key,food_label in [('chicken_kg','Tavuk eti'),('fish_kg','Balık'),('dairy_kg','Süt ürünleri')]:
            if v.get(food_key) is not None:missing.append(food_label+' miktarı kaydedildi; kaynaklı faktör tanımlanmadığı için hesaplanmadı')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Kompost yapıyorum':
        z=v.get('zuruf_ton')
        if z is not None:
            # IPCC 2006 composting default factors, wet weight; CH4=4kg/t, N2O=0.24kg/t.
            # GWP100 AR6 CH4 biogenic=27.2, N2O=273. Only a separately labeled illustrative estimate.
            rows.append({'Faaliyet':'Kompost (genel IPCC yaklaşımı; tahmini)','Modül':'Züruf (tahmini)','kg CO₂e/yıl':round(z*(4*27.2+0.24*273),3)})
            missing.append('Kompost tahmini fındık zürufuna özgü değildir; toplamdan ayrı raporlanmalı')
        else:missing.append('Kompost miktarı (ton)')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Yakıyorum':
        z=v.get('zuruf_burn_kg')
        # IPCC 2019 refinement Vol 4 Table 2.5: g/kg of dry matter ACTUALLY burnt.
        # CH4 2.7 g/kg; N2O 0.07 g/kg. GWP100: CH4 27.2, N2O 273.
        if z is not None:
            dry_fraction=v.get('zuruf_dry_fraction')
            burned_fraction=v.get('zuruf_burned_fraction')
            if dry_fraction is not None and burned_fraction is not None:
                dry_burnt=z*dry_fraction/100*burned_fraction/100
                rows.append({'Faaliyet':'Züruf açıkta yakma (IPCC genel; tahmini)',
                             'Modül':'Züruf (tahmini)',
                             'kg CO₂e/yıl':round(dry_burnt*(2.7*27.2+0.07*273)/1000,3)})
            else:missing.append('Züruf yakma: kuru madde ve yanma oranı bilinmiyor')
        else:missing.append('Züruf yakma miktarı gerekli')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Bahçede bırakıyorum':missing.append('Bahçede bırakılan zürufun toprak emisyonları (ayrı yöntem gerekli)')
    # Yayla yolculuğuna ait %20 artış yalnızca AYRI bir temel tüketim tahminiyle
    # senaryo olarak kullanılabilir; gerçek yakıt tüketimine ikinci kez eklenmez.
    if v.get('car')=='Evet' and v.get('yayla_frequency')=='Ayda 1–2 kez' and v.get('yayla_km_roundtrip') is not None and v.get('yayla_base_l100') is not None and v.get('fuel') in ('Benzin','Dizel','LPG'):
        km=v.get('yayla_km_roundtrip');rate=v.get('yayla_base_l100')
        # Bir aylık ziyaret varsayımı: kullanıcı 1 veya 2 olarak seçer.
        visits=v.get('yayla_visits_month',1)
        baseline=km*visits*12*rate/100*F[v.get('fuel')]
        rows.append({'Faaliyet':'Yayla seyahati (%20 artışlı SENARYO; ana toplam dışı)','Modül':'Yayla (senaryo)','kg CO₂e/yıl':round(baseline*1.20,3)})

    return rows,missing

def compare_models(rows):
    """Two *scope* variants with identical factors for shared activities.

    Local activities are included only in the extended Eynesil scope.
    Separate high-uncertainty residue estimates remain outside both totals.
    """
    shared = {'Enerji', 'Ulaşım', 'Plastik malzeme', 'Beslenme'}
    local = {'Tarım', 'Yerel faaliyet'}
    reference_rows = [r for r in rows if r['Modül'] in shared]
    local_rows = [r for r in rows if r['Modül'] in local]
    reference = round(sum(r['kg CO₂e/yıl'] for r in reference_rows), 3)
    increment = round(sum(r['kg CO₂e/yıl'] for r in local_rows), 3)
    extended = round(reference + increment, 3)
    return {'reference': reference, 'extended': extended,
            'increment': increment, 'shared_rows': reference_rows,
            'local_rows': local_rows}

def send_sheet(payload):
    """Tek katılımcı oturum ID'si için tek satır: tekrar gönderimde güncelle."""
    try:
        cfg=st.secrets['connections']['gsheets']
        import gspread
        from google.oauth2.service_account import Credentials
        creds=Credentials.from_service_account_info(dict(cfg['service_account']),scopes=['https://www.googleapis.com/auth/spreadsheets'])
        ws=gspread.authorize(creds).open_by_key(cfg['spreadsheet_id']).worksheet('Yanitlar')
        values=[payload['id'],payload['timestamp'],json.dumps(payload['answers'],ensure_ascii=False,default=str),json.dumps(payload['results'],ensure_ascii=False,default=str)]
        cell=ws.find(payload['id'],in_column=1)
        if cell:
            ws.update(range_name=f'A{cell.row}:D{cell.row}',values=[values],value_input_option='RAW')
        else:
            ws.append_row(values,value_input_option='RAW')
        return True,None
    except Exception as e:return False,str(e)

st.markdown('<div class="hero"><span class="pill">🌿 Eynesil için</span><h1>Karbon Rehberim</h1><div class="mini">Günlük alışkanlıklarını seç, karbon etkini keşfet ve küçük adımlarla azalt.</div></div>',unsafe_allow_html=True)
s=st.session_state.step
st.progress(s/(len(STEPS)-1))
st.caption(f"{s+1}. adım / {len(STEPS)} · {STEPS[s]}")

if s==0:
    st.subheader('Başlamaya hazır mısınız?')
    st.write('Kısa sorular soracağız. Bilmediğiniz miktarları boş bırakabilirsiniz. İsim, telefon veya adres istemiyoruz.')
    st.info('Bu uygulama araştırma prototipidir. Genel ve Eynesil kapsamları karşılaştırılır; hesaplanan değerler tüm karbon ayak iziniz değil, ölçülebilen faaliyetlerin toplamıdır.')
    st.checkbox('Anonim yanıtlarımın bilimsel araştırma için kaydedilmesine izin veriyorum.',key='consent')
    st.caption('İzin vermezseniz soruları yine yanıtlayabilir ve kendi sonucunuzu görebilirsiniz; veriniz araştırma tablosuna gönderilmez.')
    st.markdown('#### 📋 Orijinal Eynesil anketi — katılımcı bilgileri')
    select('survey_age','1. Yaş aralığınız', ['Belirtmek istemiyorum','18 yaş altı','18-25','26-40','41-60','61 ve üzeri'])
    st.number_input('2. Hane halkı sayısı',min_value=1,max_value=30,value=3,step=1,key='survey_household')
    select('survey_occupation','3. Temel geçim kaynağınız / mesleğiniz',['Belirtmek istemiyorum','Öğrenci','Kamu çalışanı','Özel sektör','Emekli','Çiftçi','Balıkçı','Esnaf','Diğer'])
elif s==1:
    st.subheader('🏠 Evinizde enerji')
    select('living_area','Genellikle hangi bölgede yaşıyorsunuz?', ['Sahil kesiminde','Sahil ile yüksek kesimler arasında','Yüksek kesimde / köyde'])
    select('season_usage','Evinizin enerji tüketimi hangi dönemde artıyor?', ['Kışın daha fazla','Yazın daha fazla','Yıl boyunca benzer','Bilmiyorum'])
    st.caption('Bu iki yanıt yerel analizde kullanılır; tek başına emisyon katsayısını değiştirmez.')
    st.number_input('Yılda yaklaşık kaç ayı kış / ısınma dönemi sayarsınız?',min_value=1,max_value=11,value=4,step=1,key='winter_months',help='Mevsimsel hesaplamada kullanılır. Emin değilseniz 4 ay bırakabilirsiniz; bu bir varsayımdır.')
    select('electric_use','Evde elektrik kullanıyor musunuz?',['Evet','Hayır','Bilmiyorum'])
    if st.session_state.electric_use=='Evet':
        line('Elektrik tüketimi','Faturanızdaki kWh değerini yazabilirsiniz. TL tutarı kWh yerine geçmez.')
        select('electric_mode','Elektrik tüketiminizi nasıl biliyorsunuz?', ['Aylık ortalama','Mevsime göre ayrı'])
        if st.session_state.electric_mode=='Mevsime göre ayrı':
            num('elec_winter','Kış aylarında ayda kaç kWh?',10)
            num('elec_other','Diğer aylarda ayda kaç kWh?',10)
        else:num('electric','Ayda yaklaşık kaç kWh elektrik tüketiyorsunuz?',10)
    st.multiselect('Evinizde kullanılan ısınma kaynakları (birden fazla seçebilirsiniz)', ['Doğalgaz','Kömür','Elektrik','Odun','Fındık kabuğu','Diğer / bilmiyorum'],key='heating_sources',help='Elektrikle ısınma evin toplam kWh tüketiminde ise ikinci kez eklenmez.')
    if 'Doğalgaz' in st.session_state.heating_sources:
        select('gas_mode','Doğalgaz tüketiminizi nasıl biliyorsunuz?', ['Aylık ortalama','Mevsime göre ayrı'])
        if st.session_state.gas_mode=='Mevsime göre ayrı':
            num('gas_winter','Kış aylarında ayda kaç m³ doğalgaz?',10)
            num('gas_other','Diğer aylarda ayda kaç m³ doğalgaz?',10)
        else:
            num('gas','Yılın 12 ayına göre ortalama aylık kaç m³ doğalgaz?',10)
            st.caption('Yalnızca kış faturasındaki tüketimi biliyorsanız mevsime göre ayrı seçeneğini kullanın.')
    if 'Kömür' in st.session_state.heating_sources:num('coal','Bir kışta yaklaşık kaç kg kömür kullanıyorsunuz?',25)
    if 'Odun' in st.session_state.heating_sources:num('wood_kg','Bir kışta yaklaşık kaç kg odun kullanıyorsunuz?',25)
    if 'Fındık kabuğu' in st.session_state.heating_sources:
        num('shell_kg','Bir kışta yaklaşık kaç kg fındık kabuğu yakıyorsunuz?',25)
        with st.expander('🔬 Fındık kabuğu alt ısıl değeri (araştırmacı)'):
            st.number_input('Alt ısıl değer (MJ/kg)',min_value=1.0,max_value=35.0,value=15.6,step=0.1,key='shell_ncv')
            st.caption('15,6 MJ/kg, IPCC odun/odun atığı varsayımıdır; fındık kabuğu için ölçülmüş değer DEĞİLDİR. Yerel laboratuvar değeri elde edilirse değiştirin.')
    if 'Elektrik' in st.session_state.heating_sources:st.caption('Elektrikli ısıtma evin toplam elektrik tüketimine dâhilse yeniden sayılmayacaktır.')
    if any(x in st.session_state.heating_sources for x in ('Odun','Fındık kabuğu')):st.info('IPCC 2006 konut biyokütle yakma CH₄/N₂O genel faktörleri kullanılır. Biyojenik CO₂ ayrı raporlanır. Fındık kabuğu alt ısıl değeri odun vekilidir; ölçülmüş yerel katsayı değildir.')
elif s==2:
    st.subheader('🚗 Günlük ulaşım')
    st.caption('Orijinal anketin 7–10. soruları korunmuştur. İş/okul ulaşımı haftalık toplam mesafeye dahildir; ikinci kez eklenmez.')
    select('commute_mode','10. İş veya okula giderken hangi ulaşımı kullanıyorsunuz?', ['Özel araç','Toplu taşıma / dolmuş','Yürüyerek','Bisiklet','Servis','İşe/okula gitmiyorum','Diğer'])
    select('car','7. Özel araç kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.car=='Evet':
        select('fuel','8. Araç yakıt türü',['Benzin','Dizel','LPG','Elektrik','Bilmiyorum'])
        if st.session_state.fuel in ('Benzin','Dizel','LPG'):
            select('car_input','Özel araç kullanımınızı nasıl belirtmek istersiniz?',['Haftalık yol (km)','Haftalık yakıt (litre)','Bilmiyorum'])
            if st.session_state.car_input=='Haftalık yakıt (litre)':num('car_liters','Haftada yaklaşık kaç litre yakıt kullanıyorsunuz?',5)
            elif st.session_state.car_input=='Haftalık yol (km)':
                num('car_km','7. Şahsi aracınızla haftada toplam kaç km yol yapıyorsunuz? (iş/okul ve diğer yolculuklar dahil)',10)
                num('car_rate','Aracınız 100 km’de kaç litre yakıyor?',0.5)
    st.markdown('#### 🏔️ Köy ve yayla yolları')
    select('road_type','En çok hangi yollarda araç kullanıyorsunuz?',
           ['Karışık yollar','Düz / sahil yolları','Yokuşlu köy / yayla yolları','Araç kullanmıyorum'])
    select('yayla_frequency','Köy veya yaylaya araçla ne sıklıkla gidiyorsunuz?',
           ['Ayda 1–2 kez','Hiç','Yılda birkaç kez','Haftada en az bir kez'])
    st.caption('Yerel saha beyanı: yaylalar yaklaşık 2.000 m; ortalama ayda 1 ziyaret; yokuşta yaklaşık %20 fazla yakıt. Bu %20 doğrulanmış katsayı değil, isteğe bağlı senaryodur. Gerçek yakıt tüketimine ayrıca eklenmez.')
    if st.session_state.get('car')=='Evet' and st.session_state.get('yayla_frequency')=='Ayda 1–2 kez':
        with st.expander('🏔️ İsteğe bağlı yayla yolculuğu senaryosu'):
            st.caption('Ana karbon toplamından ayrı gösterilir. Yalnızca yayla seyahatine ait düz yol tüketimi tahmini biliniyorsa hesaplanır.')
            num('yayla_km_roundtrip','Yaylaya gidiş-dönüş toplam kaç km?',5)
            num('yayla_base_l100','Aracın düz yoldaki tüketimi (L/100 km)',0.5)
            st.selectbox('Ayda kaç kez gidiyorsunuz?',[1,2],key='yayla_visits_month')
    select('bus','9. Eynesil–Giresun / Eynesil–Trabzon dolmuş veya otobüs kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.commute_mode=='Toplu taşıma / dolmuş':
        st.caption('İş/okul yolculuklarınızı aşağıdaki haftalık toplu taşıma sefer sayısına dahil edin; ayrıca eklenmeyecektir.')
    if st.session_state.bus=='Evet':
        select('bus_route','9. Hangi hatta yolculuk yapıyorsunuz?',['Eynesil–Trabzon','Eynesil–Giresun','Diğer'])
        if st.session_state.bus_route in ROUTES:
            select('bus_trip_type','Yolculuğunuz nasıl?',['Gidiş-dönüş','Tek yön'])
            st.number_input('Haftada kaç kez bu yolculuğu yapıyorsunuz?',min_value=0,max_value=21,value=1,step=1,key='bus_trips_week')
            route_km=ROUTES[st.session_state.bus_route]['km']
            multiplier=2 if st.session_state.bus_trip_type=='Gidiş-dönüş' else 1
            st.caption(f'Haftalık hesaplanan mesafe: {route_km*st.session_state.bus_trips_week*multiplier:g} km. Gidiş-dönüş seçildiğinde iki yön de hesaplanır.')
        else:
            num('bus_km','Haftada yaklaşık kaç km yolculuk yapıyorsunuz? (gidiş-dönüş toplam)',5)
        st.caption('Saha tahmini: her hatta günde 6 sefer; minibüste ortalama 8,5 yolcu. Hat seçilirse yakıt tüketimi otomatik kullanılır. Haftalık mesafeye sefer sayısı tekrar eklenmez.')
        if st.session_state.bus_route in ROUTES:
            r=ROUTES[st.session_state.bus_route]
            st.info(f"{st.session_state.bus_route}: {r['km']:g} km/tek yön, {2*r['km']:g} km/gidiş-dönüş. Tahmini {r['liters_trip']:g} L motorin/tek yön. 8,5 yolcu varsayımı.")
        else:
            with st.expander('🔬 Diğer hat için araştırmacı yakıt verisi'):
                num('local_minibus_l100','Minibüs tüketimi (L/100 km)',1)
                st.caption('Doğrulanmış değer yoksa boş bırakın; tahmin yapılmaz.')
elif s==3:
    st.subheader('🌰 Tarım ve yerel yaşam')
    select('farm','Fındık veya çay tarımıyla ilgileniyor musunuz?',['Hayır','Evet'])
    if st.session_state.farm=='Evet':
        select('fert','Kimyasal gübre kullanıyor musunuz?',['Hayır','Evet','Bilmiyorum'])
        if st.session_state.fert=='Evet':
            num('bags','Yılda kaç torba gübre kullanıyorsunuz?')
            num('bag_weight','Bir torba kaç kg?',5)
            num('n_percent','Paket üzerindeki azot (N) yüzdesi kaç?',1)
        select('zuruf','Fındık zürufunu ne yapıyorsunuz?',['Yok','Bahçede bırakıyorum','Kompost yapıyorum','Yakıyorum','Bilmiyorum'])
        if st.session_state.zuruf=='Kompost yapıyorum':
            with st.expander('🌿 Kompost miktarını biliyor musunuz? (isteğe bağlı)'):
                num('zuruf_ton','Yılda yaklaşık kaç ton yaş züruf kompostluyorsunuz?',0.1)
                st.caption('Genel IPCC kompost emisyon faktörleriyle yaklaşık hesaplanır; fındık zürufuna özgü değildir.')
        if st.session_state.zuruf=='Yakıyorum':
            num('zuruf_burn_kg','Yılda yaklaşık kaç kg züruf yakıyorsunuz? (yaş tartım)',10)
            with st.expander('🔬 Züruf yakma varsayımları (araştırmacı)'):
                st.caption('IPCC tarımsal kalıntı genel faktörleri. Zürufa özgü ölçüm değildir. Kuru madde ve gerçekten yanan oranı doğrulanmadan tahmin üretmeyiz.')
                num('zuruf_dry_fraction','Kuru madde oranı (%)',5)
                num('zuruf_burned_fraction','Kuru maddenin gerçekten yanan oranı (%)',5)
    select('boat','Balıkçı teknesinin yakıtını siz mi karşılıyorsunuz?',['Hayır','Evet'])
    if st.session_state.boat=='Evet':
        select('boat_fuel','Teknenin yakıtı nedir?',['Dizel','Benzin','Bilmiyorum'])
        if st.session_state.boat_fuel!='Bilmiyorum':
            num('boat_liters','Aktif olduğunuz bir haftada ortalama kaç litre tekne yakıtı kullanılıyor?',5)
            st.number_input('Yılda kaç hafta balıkçılık yapılıyor?',min_value=0,max_value=52,value=None,step=1,key='boat_active_weeks',help='Mevsimlik faaliyetler için 52 hafta varsayılmaz; gerçekten aktif olunan hafta sayısını girin.')
            select('boat_allocation','Tekne yakıtını nasıl raporlayalım?',['Teknenin tüm yakıtı','Kişi başına eşit pay'])
            if st.session_state.boat_allocation=='Kişi başına eşit pay':
                st.caption('Eşit paylaştırma yalnızca açık bir tahsis varsayımıdır; kişi sayısını belirtin.')
                num('boat_people','Teknedeki paylaştırılacak kişi sayısı',1)
elif s==4:
    st.subheader('♻️ Günlük alışkanlıklar')
    select('survey_recycling','6. Kâğıt, cam ve plastikleri geri dönüşüm kutusuna atıyor musunuz?',['Evet','Hayır','Bazen'])
    st.markdown('#### ♻️ DOA depozito iadesi — isteğe bağlı')
    select('doa_use','DOA uygulamasıyla depozitolu ambalaj iade ediyor musunuz?',['Hayır','Evet'])
    if st.session_state.doa_use=='Evet':
        st.caption('DOA uygulamasındaki aylık iade adetlerinize bakabilirsiniz. Yalnızca gerçekten teslim ettiğiniz ambalajları sayın.')
        st.number_input('Son bir ayda DOA’ya iade ettiğiniz PET şişe (adet)',min_value=0,max_value=5000,value=0,step=1,key='doa_pet_month')
        st.number_input('Son bir ayda DOA’ya iade ettiğiniz cam şişe (adet)',min_value=0,max_value=5000,value=0,step=1,key='doa_glass_month')
        with st.expander('🔬 Şişe ağırlıkları ve yöntem (araştırmacı)'):
            st.caption('20 g PET ve 250 g cam yalnızca örnek kütle varsayımlarıdır; yerel tartımla güncellenmelidir.')
            st.number_input('PET şişe başına gram',min_value=1.0,max_value=500.0,value=20.0,step=1.0,key='doa_pet_g')
            st.number_input('Cam şişe başına gram',min_value=1.0,max_value=3000.0,value=250.0,step=10.0,key='doa_glass_g')
        st.caption('Geri dönüşüm yararı, EPA WARM v16 ABD senaryosuna göre düzenli depolama ile karşılaştırılır. Türkiye’de gerçekleşen net tasarruf değildir; ana ayak izinden düşülmez.')
    select('survey_bag_reuse','5. Aldığınız plastik poşetleri yeniden kullanma sıklığınız nedir?',['Her zaman','Çoğu zaman','Bazen','Hiçbir zaman'])
    select('plastic','Plastik poşet veya PET şişe kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.plastic=='Evet':
        num('bags_week','Haftada yaklaşık kaç poşet?',1)
        num('bottles_week','Haftada yaklaşık kaç PET şişe?',1)
        with st.expander('⚖️ Ürün ağırlıkları (isterseniz değiştirin)'):
            st.caption('Poşet ve şişe ağırlıkları kişiden kişiye değişir. Aşağıdaki değerler yalnızca örnek varsayımlardır.')
            st.number_input('Bir poşet kaç gram?',min_value=0.1,value=5.0,step=0.5,key='bag_g')
            st.number_input('Bir boş PET şişe gövdesi kaç gram?',min_value=0.1,value=20.0,step=1.0,key='bottle_g')
    select('garden_food','Sebze ve meyvenizin bir bölümünü kendi bahçenizden karşılıyor musunuz?',['Hayır','Evet'])
    if st.session_state.garden_food=='Evet':
        st.slider('Tükettiğiniz sebze-meyvenin yaklaşık yüzde kaçı kendi bahçenizden?',0,100,25,5,key='garden_share')
        st.caption('Bu oran araştırmada kullanılır; bahçe ürünü otomatik sıfır emisyon sayılmaz. Üretim emisyonları ve ulaşım ayrı değerlendirilir.')
    select('shopping_place','Gıdayı çoğunlukla nereden temin ediyorsunuz?',['Market','Halk pazarı','Her ikisi','Kendi bahçem / üretimim'])
    select('food','Beslenme alışkanlığınızı araştırmada değerlendirmek ister misiniz?',['Hayır','Evet'])
    if st.session_state.food=='Evet':
        st.caption('Sığır eti için haftalık yaklaşık miktar yeterli. Diğer etleri aynı faktörle hesaplamıyoruz.')
        num('beef_kg','Haftada yaklaşık kaç kg sığır eti tüketiyorsunuz?',0.1)
        with st.expander('Diğer gıda tüketimi (H2: yalnızca faaliyet verisi)'):
            st.caption('Doğrulanmış ürün bazlı yaşam döngüsü faktörü olmadan bu girdilerden emisyon hesaplanmaz.')
            num('chicken_kg','Haftada kaç kg tavuk eti?',0.1)
            num('fish_kg','Haftada kaç kg balık?',0.1)
            num('dairy_kg','Haftada kaç kg süt ürünü?',0.1)
    st.caption('Kendi bahçesinden üretim ve pazar/market tercihi, tek başına indirim katsayısı değildir. Gıda üretim miktarı ve ulaşım verisi olmadan hayalî tasarruf hesaplanmaz.')
else:
    st.subheader('🌱 Karbon özetiniz')
    rows,missing=calculate();verified=[r for r in rows if r['Modül'] not in ('Züruf (tahmini)','Yayla (senaryo)','Biyojenik CO₂ (ayrı)')];estimates=[r for r in rows if '(tahmini)' in r['Modül']];total=sum(r['kg CO₂e/yıl'] for r in verified)
    comparison=compare_models(rows)
    st.metric('Hesaplanabilen yıllık emisyon',f'{total:,.0f} kg CO₂e')
    st.caption('Bu bir **kısmi, varsayımlara dayalı emisyon tahminidir**; hesaplanamayan faaliyetler sıfır sayılmaz. Farklı yaşam döngüsü sınırları içeren bileşenler ayrı yorumlanmalıdır.')
    st.markdown('### 🔬 Emisyon faktörü duyarlılığı (H1–H2 için belirsizlik değerlendirmesi)')
    st.caption('Bu analiz, yalnızca hesaplanan elektrik ve yakıt emisyon faktörlerini varsayımsal ±%10 değiştirir; güven aralığı değildir ve yerel katsayı üretmez.')
    sensitive=sum(r['kg CO₂e/yıl'] for r in verified if r['Faaliyet'] in ('Elektrik','Doğalgaz','Kömür','Özel araç','Balıkçı teknesi') or r['Faaliyet'].startswith(('Odun yakımı','Fındık kabuğu CH₄')))
    st.write(f'İlgili faaliyetlerin referans toplamı: **{sensitive:,.1f} kg CO₂e/yıl** · Alt senaryo: **{sensitive*0.9:,.1f}** · Üst senaryo: **{sensitive*1.1:,.1f}**')
    if st.session_state.get('doa_use')=='Evet':
        d=doa_scenario(st.session_state.get('doa_pet_month',0),st.session_state.get('doa_glass_month',0),st.session_state.get('doa_pet_g',20.0),st.session_state.get('doa_glass_g',250.0))
        saving=sum(item['potential_kg_co2e'] for item in d.values())
        st.markdown('### ♻️ DOA iade senaryosu — ayrı gösterim')
        st.metric('Olası yıllık geri dönüşüm avantajı',f'{saving:,.2f} kg CO₂e/yıl')
        st.caption(f"Yıllık PET: {d['PET']['annual_kg']:.2f} kg · Cam: {d['Cam']['annual_kg']:.2f} kg. Son bir ayın 12 ay boyunca temsilî olduğu varsayılmıştır.")
        st.info('Bu bir **ABD EPA WARM karşılaştırma senaryosudur**, DOA sisteminin doğrulanmış net karbon tasarrufu değildir. Ambalajların fiilen geri dönüştürülmesi, nakliye ve Türkiye enerji karması sonucu değiştirebilir. Ana karbon toplamından çıkarılmamıştır.')
    st.markdown('### 🎯 H3: Birleşik enerji ve ulaşım senaryosu')
    st.caption('Elektrik azaltımı ve özel araçtan minibüse geçiş tek hesapta değerlendirilir. Özel araçtan azaltılan mesafe ikinci kez azaltılmaz; yeni minibüs emisyonu eklenir. Gerçekleşmiş tasarruf değildir.')
    base_by_name={r['Faaliyet']:r['kg CO₂e/yıl'] for r in verified}
    electric_pct=st.slider('Elektrik tüketimini azaltma (%)',0,50,10,5,key='v16_electric_pct')
    car_pct=st.slider('Özel araç kilometresini azaltma / minibüse aktarma (%)',0,50,10,5,key='v16_car_pct')
    has_car='Özel araç' in base_by_name
    replacement=0.0
    shift_mode='Yolculuk yapılmayacak (talep azaltımı)'
    if has_car:
        shift_mode=st.selectbox('Azaltılan özel araç mesafesi nasıl karşılanacak?', ['Yolculuk yapılmayacak (talep azaltımı)','Minibüse geçilecek'],key='v16_shift_mode')
        if shift_mode=='Minibüse geçilecek':
            if st.session_state.get('car_input')=='Haftalık yol (km)' and st.session_state.get('car_km') is not None and st.session_state.get('bus_route') in ROUTES:
                r=ROUTES[st.session_state['bus_route']]
                km_shift=st.session_state['car_km']*52*car_pct/100
                replacement=km_shift*r['liters_trip']/r['km']/LOCAL['minibus_passengers_mean']*F['Dizel']
                st.caption(f'İkame mesafesi: {km_shift:,.1f} km/yıl; yeni minibüs emisyonu: {replacement:,.1f} kg CO₂e/yıl. Aynı mesafe ve ortalama 8,5 yolcu varsayılmıştır.')
            else:
                st.warning('Minibüse geçiş için özel araç haftalık km ve Eynesil minibüs güzergâhı gerekli. Bu bilgiler olmadan net senaryo hesaplanmaz.')
    valid_shift=(shift_mode!='Minibüse geçilecek' or (st.session_state.get('car_input')=='Haftalık yol (km)' and st.session_state.get('car_km') is not None and st.session_state.get('bus_route') in ROUTES))
    if valid_shift and ('Elektrik' in base_by_name or has_car):
        outcome=integrated_scenario(base_by_name,electric_pct/100 if 'Elektrik' in base_by_name else 0,car_pct/100 if has_car else 0,replacement)
        a,b,c=st.columns(3)
        a.metric('Mevcut',f"{outcome['baseline']:,.0f} kg")
        b.metric('Alternatif',f"{outcome['alternative']:,.0f} kg")
        c.metric('Net azalma',f"{outcome['difference']:,.0f} kg")
        st.caption(f"Yıllık net değişim: %{outcome['percent']:.1f}. Bu değer yalnızca hesaplanan faaliyetler için geçerlidir.")
    elif valid_shift:st.info('Elektrik veya özel araç tüketimi hesaplandığında senaryo gösterilir.')
    if st.session_state.get('bus')=='Evet' and st.session_state.get('bus_route') in ROUTES and st.session_state.get('bus_trips_week') is not None:
        st.markdown('### 🔬 Minibüs duyarlılık analizi (araştırma hedefi 7)')
        r=minibus_range(st.session_state['bus_route'],st.session_state['bus_trips_week'],st.session_state.get('bus_trip_type','Gidiş-dönüş')=='Gidiş-dönüş')
        st.dataframe(pd.DataFrame([{'Varsayım':'Düşük tüketim / 9 yolcu','kg CO₂e/yıl':round(r['low'],2)},
                                   {'Varsayım':'Orta tüketim / 8,5 yolcu','kg CO₂e/yıl':round(r['central'],2)},
                                   {'Varsayım':'Yüksek tüketim / 8 yolcu','kg CO₂e/yıl':round(r['high'],2)}]),hide_index=True,use_container_width=True)
        st.caption('Bu aralık, verilen saha tahminleriyle yapılan senaryo duyarlılığıdır; istatistiksel güven aralığı veya ölçüm doğrulaması değildir.')
    st.markdown('### 🔬 H1: Aynı ulaşım faaliyeti için standart–yerel karşılaştırma')
    st.caption('Aynı yolcu-km üzerinden iki yöntem karşılaştırılır. Standart yolcu-km katsayısı belgelenmeden H1 için sayısal sonuç oluşturulmaz.')
    if st.session_state.get('bus')=='Evet' and st.session_state.get('bus_route') in ROUTES:
        with st.expander('Araştırmacı: kaynaklandırılmış standart minibüs faktörü'):
            standard_factor=st.number_input('Standart minibüs faktörü (kg CO₂e/yolcu-km)',min_value=0.0,value=0.0,step=0.001,format='%.3f',key='standard_bus_factor')
            st.caption('0,000 = doğrulanmış standart faktör henüz tanımlanmadı. Faktörün yayın/yıl/araç sınıfını araştırma notlarına ekleyin.')
            st.text_input('Standart faktör kaynağı ve yılı',key='standard_bus_source')
        if standard_factor>0 and st.session_state.get('standard_bus_source','').strip():
            h1=comparable_minibus(st.session_state['bus_route'],st.session_state.get('bus_trips_week',0),standard_factor,st.session_state.get('bus_trip_type')=='Gidiş-dönüş')
            st.dataframe(pd.DataFrame([{'Yöntem':'Standart faktör','kg CO₂e/yıl':round(h1['standard_kg'],2)},{'Yöntem':'Yerel yakıt/doluluk varsayımı','kg CO₂e/yıl':round(h1['local_kg'],2)}]),hide_index=True,use_container_width=True)
            st.caption(f"H1 farkı (yerel - standart): {h1['difference_kg']:+.2f} kg CO₂e/yıl. Bu karşılaştırma tek bir ulaşım bileşenine aittir, H1'i istatistiksel olarak kanıtlamaz.")
        else:st.info('H1 için standart minibüs faktörü ve kaynağı girilmedi; karşılaştırma üretilmedi.')
    st.markdown('### 🧪 H2: Yerel faaliyet kapsamı ve veri sınırları')
    st.caption('Fındık/çay gübresinin doğrudan N₂O emisyonu, tekne yakıtı ve ısınma faaliyetleri H2 için hesaplanabilir bileşenlerdir. Fındık zürufu, diğer gıdalar ve dolaylı gübre emisyonları gerekli kaynak/ölçüm olmadan sıfır sayılmaz. H2, ikinci veri setinde dağılımlar incelenmeden doğrulanmış kabul edilmez.')
    st.markdown('### 🌍 Kapsam karşılaştırması (yerel katsayı etkisi değildir)')
    left,right=st.columns(2)
    with left: st.metric('Genel kapsam',f"{comparison['reference']:,.0f} kg CO₂e/yıl")
    with right: st.metric('Eynesil genişletilmiş kapsam',f"{comparison['extended']:,.0f} kg CO₂e/yıl")
    st.metric('Yerel faaliyetlerin eklenen katkısı',f"+{comparison['increment']:,.0f} kg CO₂e/yıl")
    st.caption('**Bu bir tasarruf ya da iki farklı emisyon katsayısının karşılaştırması değildir.** Genel kapsamda enerji, ulaşım, plastik malzeme ve hesaplanan beslenme; genişletilmiş kapsamda bunlara ölçülebilen gübre ve tekne yakıtı faaliyetleri eklenir. Aynı ortak faaliyet iki kez sayılmaz.')
    st.caption('Her iki kapsamda da mevcut ulusal/uluslararası referans faktörleri kullanılır. Eynesil için ölçülmüş yeni bir emisyon katsayısı henüz yoktur. Eksik faaliyetler ve zürufun ayrı belirsiz tahminleri iki toplamın da dışındadır.')
    if comparison['increment'] > 0:
        st.bar_chart(pd.DataFrame({'kg CO₂e/yıl':[comparison['reference'],comparison['extended']]},index=['Genel kapsam','Eynesil genişletilmiş']))
    elif st.session_state.get('farm')=='Evet' or st.session_state.get('boat')=='Evet':
        st.info('Yerel faaliyet bildirdiniz ancak sayısal yerel katkı henüz hesaplanmamış olabilir. Eksik girdileri kontrol edin.')
    else:
        st.info('Yerel tarım veya tekne yakıtı faaliyeti bildirilmediği için iki kapsamın sonucu aynıdır.')
    with st.expander('🔬 Karşılaştırmanın ayrıntıları (araştırmacı)'):
        st.write('Genel kapsam bileşenleri')
        if comparison['shared_rows']:st.dataframe(pd.DataFrame(comparison['shared_rows']),hide_index=True,use_container_width=True)
        else:st.caption('Hesaplanan ortak faaliyet yok.')
        st.write('Eynesil kapsamında eklenen faaliyetler')
        if comparison['local_rows']:st.dataframe(pd.DataFrame(comparison['local_rows']),hide_index=True,use_container_width=True)
        else:st.caption('Hesaplanan ek yerel faaliyet yok.')
        st.caption('Mevsimlik enerji tüketimi ve gerçek araç yakıtı her iki modelde aynıdır. Yaşam bölgesi, yol türü ve yayla sıklığı açıklayıcı araştırma değişkenleridir; doğrulanmamış çarpan uygulanmaz.')

    road=v_road=st.session_state.get('road_type','Karışık yollar')
    yayla=st.session_state.get('yayla_frequency','Ayda 1–2 kez')
    st.caption(f'🏔️ Yerel ulaşım: {road} · Köy/yayla: {yayla}. 2.000 m rakım ve %20 tüketim artışı kullanıcı saha varsayımıdır; ana toplama uygulanmaz.')
    st.caption(f'🌦️ Yaşam bölgesi: {st.session_state.get("living_area","Belirtilmedi")} · Mevsimsel enerji durumu: {st.session_state.get("season_usage","Belirtilmedi")}. Mevsimlik tüketim girildiyse gerçek miktarlar kullanılır; iklim için keyfî çarpan uygulanmaz.')
    if st.session_state.get('garden_food')=='Evet':
        st.caption(f"🥬 Sebze-meyvenin kendi bahçesinden karşılanan payı: %{st.session_state.get('garden_share',0)}. Üretim miktarı ve yetiştirme koşulları bilinmediğinden otomatik karbon indirimi yapılmadı.")
    yayla_scenario=[r for r in rows if r['Modül']=='Yayla (senaryo)']
    if yayla_scenario:st.info(f'🏔️ Yayla yolculuğu için %20 artışlı varsayımsal senaryo: {yayla_scenario[0]["kg CO₂e/yıl"]:,.1f} kg CO₂e/yıl (ana toplam dışında; gerçek yakıt tüketimiyle çifte sayılmamalı).')
    if estimates:st.info('🌰 Züruf için ayrı, yöntemsel belirsizliği yüksek tahmin: '+f"{sum(r['kg CO₂e/yıl'] for r in estimates):,.1f} kg CO₂e/yıl"+' (ana toplama eklenmedi).')
    if verified:
        df=pd.DataFrame(verified)
        by=df.groupby('Modül')['kg CO₂e/yıl'].sum().sort_values(ascending=False)
        st.bar_chart(by)
        biggest=max(verified,key=lambda r:r['kg CO₂e/yıl'])
        st.warning(f"En yüksek hesaplanan kaynak: **{biggest['Faaliyet']}** ({biggest['kg CO₂e/yıl']:,.0f} kg CO₂e/yıl)")
        advice={'Elektrik':'Kullanılmayan cihazları kapatmak ve verimli aydınlatma seçmek elektrik tüketimini azaltabilir.',
                'Doğalgaz':'Isıtma ayarlarını ve yalıtımı gözden geçirmek tüketimi azaltabilir.',
                'Kömür':'Isı kayıplarını azaltmak kömür tüketimini düşürebilir.',
                'Özel araç':'Uygunsa yürüyüş, ortak araç veya toplu taşıma tercih edebilirsiniz.',
                'Balıkçı teknesi (tam yakıt)':'Motor bakımı ve verimli seyir planlaması yakıt tüketimini azaltabilir.',
                'Balıkçı teknesi (kişi payı)':'Motor bakımı ve verimli seyir planlaması yakıt tüketimini azaltabilir.',
                'Gübre: doğrudan N₂O':'Toprak analizi ve uygun gübreleme planı için tarım uzmanına danışabilirsiniz.'}
        st.success('💡 Size özel öneri: '+advice.get(biggest['Faaliyet'],'Tüketim miktarlarını gözden geçirebilirsiniz.'))
        eligible=[r for r in verified if r['Faaliyet'] in ('Elektrik','Doğalgaz','Kömür','Özel araç','Balıkçı teknesi')]
        if eligible:
            st.markdown('#### 🎯 Ne kadar azaltabilirsiniz?')
            opts={r['Faaliyet']:r['kg CO₂e/yıl'] for r in eligible}
            activity=st.selectbox('Azaltmak istediğiniz alan',list(opts),key='scenario_activity')
            pct=st.slider('Tüketimi ne kadar azaltabilirsiniz?',5,40,10,5,key='scenario_pct')
            saving=opts[activity]*pct/100
            st.metric('Tahmini yıllık azaltım',f'{saving:,.0f} kg CO₂e')
            st.caption('Diğer koşullar sabit varsayılır. Alternatif ulaşım/ısıtma emisyonları ve maliyetler dahil değildir; gerçekleşmiş tasarruf değildir.')
    else:st.info('Sayısal sonuç için en az bir tüketim miktarı girmeniz gerekiyor. Yanıtlarınızı geri dönüp tamamlayabilirsiniz.')
    if missing:
        with st.expander(f'ℹ️ Henüz hesaplanamayan alanlar ({len(set(missing))})'):
            for item in dict.fromkeys(missing):st.write('• '+item)
    with st.expander('🔬 Kaynaklar ve hesaplama sınırları'):
        st.write('DOA iade senaryosu: EPA WARM v16 (Aralık 2023), PET geri dönüşüm -1,04 ve düzenli depolama +0,02; cam geri dönüşüm -0,28 ve düzenli depolama +0,02 MT CO₂e/ABD short ton. 1 short ton=907,18474 kg. ABD referansı; Türkiye için ölçülmüş sonuç değil. https://www.epa.gov/system/files/documents/2023-12/warm_containers_packaging_and_non-durable_goods_materials_v16_dec.pdf ; https://www.epa.gov/system/files/documents/2024-01/warm_management_practices_v16_dec.pdf')
        st.write('Odun ve fındık kabuğu: IPCC 2006 Vol.2 Ch.2 Table 2.5 konut yakımı; CH₄ 300 kg/TJ, N₂O 4 kg/TJ; odun alt ısıl değer 15,6 MJ/kg. Fındık kabuğunda odun alt ısıl değeri yalnızca vekil varsayımdır. Biyojenik CO₂ ana toplam dışında ayrı gösterilir. https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf')
        st.write('V16 H2: Gübre azot girdisi torba × kg/torba × N oranı ile hesaplanır; doğrudan N₂O için IPCC 2019 yaklaşımı korunur. Dolaylı N₂O parametreleri doğrulanmadan hesaplanmaz. Balıkçı teknesi yakıtı ya tam tekne toplamı ya da açıkça belirtilen kişi payıdır, ikisi birlikte toplanmaz. Diğer gıdalar için ürün bazlı doğrulanmış faktör olmadan emisyon yazılmaz.')
        st.write('Elektrik: Türkiye EVÇED 2023, 0,469 kg CO₂e/kWh. Yakıt: DESNZ 2026 doğrudan yanma referansları. Gübre: IPCC 2019 doğrudan N₂O EF₁=0,010 ve GWP100=273. Plastik: DESNZ 2025 birincil LDPE 2,96508 ve PET 3,86390 kg CO₂e/kg; örnek ağırlıklar kullanıcı tarafından değiştirilebilir. Sığır eti: Poore & Nemecek 2018 / Our World in Data küresel ortalama 99,48 kg CO₂e/kg ürün; yaşam döngüsü kapsamı yakıt faktörlerinden farklıdır. Kompost: IPCC 2006 genel 4 kg CH₄/t ve 0,24 kg N₂O/t yaş malzeme, yalnızca ayrı tahmin. Bu referanslar Eynesil ölçümü değildir. Minibüs: Eynesil–Giresun 73 km ve tahmini 6,5–7,5 L/sefer; Eynesil–Trabzon 59 km ve tahmini 5–6 L/sefer; hesapta sırasıyla 7 ve 5,5 L kullanılır. Ortalama doluluk 8,5 yolcu; hat başına 6 günlük sefer. Bunlar doğrulanmamış yerel saha tahminleridir. Züruf açıkta yakma: IPCC 2019 Vol.4 Tablo 2.5, CH₄=2,7 g/kg ve N₂O=0,07 g/kg gerçekten yanan kuru kalıntı. Kuru madde/yanma oranı yerel veri gerektirir. Kendi bahçesinden üretim sıfır emisyon değildir.')
        if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    answers={k:v for k,v in st.session_state.items() if k not in ('sid','step','submitted') and not k.startswith('FormSubmitter') and k not in ('scenario_activity','scenario_pct','last_saved_fingerprint')}
    payload={'id':st.session_state.sid,'timestamp':datetime.now(timezone.utc).isoformat(),'answers':answers,'results':{'total_kg':round(total,3),'activities':rows,'missing':missing,'estimate_only':estimates,'model_comparison':{'reference_kg':comparison['reference'],'eynesil_extended_kg':comparison['extended'],'local_activity_contribution_kg':comparison['increment'],'comparison_type':'scope_only_not_savings'}}}
    st.download_button('📥 Yanıtlarımı indir (JSON)',data=json.dumps(payload,ensure_ascii=False,indent=2,default=str),file_name='karbon_yanitim.json',mime='application/json',use_container_width=True)
    fingerprint=json.dumps({'answers':answers,'results':payload['results']},ensure_ascii=False,sort_keys=True,default=str)
    if st.session_state.get('consent'):
        unchanged=st.session_state.last_saved_fingerprint==fingerprint
        if unchanged:st.success('Bu yanıt sürümü araştırma tablosuna kaydedildi.')
        elif st.button('📤 Anonim yanıtımı araştırmaya gönder / güncelle',type='primary',use_container_width=True):
            ok,err=send_sheet(payload)
            if ok:
                st.session_state.last_saved_fingerprint=fingerprint
                st.session_state.submitted=True
                st.rerun()
            else:st.error('Kayıt yapılamadı. Araştırmacı Google Sheets bağlantısını kontrol etmelidir. Yanıtlarınızı indirebilirsiniz.')
    else:st.caption('Araştırma izni verilmediğinden yanıtlarınız sunucuya gönderilmez.')

st.divider()
c1,c2=st.columns(2)
with c1:
    if st.button('← Geri',disabled=s==0,use_container_width=True):st.session_state.step-=1;st.rerun()
with c2:
    if st.button('Sonucumu gör 🌿' if s==4 else 'Devam et →',disabled=s==5,type='primary',use_container_width=True):st.session_state.step+=1;st.rerun()
