"""Eco-Algoritma V5 | Mobile survey, reference and Eynesil-extended comparison.
Run: pip install streamlit pandas gspread google-auth
     streamlit run eco_algoritma_v5_karsilastirma.py
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

F = {"elektrik":0.469,"gaz":2.02633,"komur":2.90495,"Benzin":2.075,"Dizel":2.58354,"LPG":1.55713,"LDPE":2.96508,"PET":3.86390,"beef":99.48}
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
    if v.get('heat')=='Doğalgaz':
        if v.get('gas_mode')=='Mevsime göre ayrı':
            winter=v.get('gas_winter');summer=v.get('gas_other');months=v.get('winter_months',4)
            annual_gas=(winter*months+summer*(12-months)) if winter is not None and summer is not None else None
        else: annual_gas=annualize(v.get('gas'),'ay')
        add('Doğalgaz','Enerji',annual_gas,F['gaz'])
    elif v.get('heat')=='Kömür':add('Kömür','Enerji',v.get('coal'),F['komur'])
    elif v.get('heat') in ('Odun / fındık kabuğu','Diğer / bilmiyorum'):missing.append('Isınma kaynaklı diğer emisyonlar')
    if v.get('car')=='Evet':
        fuel=v.get('fuel')
        if fuel in ('Benzin','Dizel','LPG'):
            if v.get('car_input')=='Haftalık yakıt (litre)':a=annualize(v.get('car_liters'),'hafta')
            elif v.get('car_input')=='Haftalık yol (km)':
                km=v.get('car_km');rate=v.get('car_rate');a=km*52*rate/100 if km is not None and rate is not None else None
            else:a=None
            add('Özel araç','Ulaşım',a,F[fuel])
        else:missing.append('Özel araç enerji tüketimi')
    if v.get('farm')=='Evet' and v.get('fert')=='Evet':
        b=v.get('bags');m=v.get('bag_weight');p=v.get('n_percent')
        nitrogen=b*m*p/100 if all(x is not None for x in (b,m,p)) else None
        add('Gübre: doğrudan N₂O','Tarım',nitrogen,0.010*(44/28)*273)
        missing.append('Gübrenin dolaylı N₂O ve üretim emisyonları')
    if v.get('farm')=='Evet' and v.get('zuruf') not in ('Yok','Bilmiyorum',None):missing.append('Fındık zürufu emisyonu')
    if v.get('boat')=='Evet':
        fuel=v.get('boat_fuel')
        if fuel in ('Benzin','Dizel'):add('Balıkçı teknesi','Yerel faaliyet',annualize(v.get('boat_liters'),'hafta'),F[fuel])
        else:missing.append('Tekne yakıtı')
    if v.get('plastic')=='Evet':
        for label,count_key,weight_key,ef in [('Poşet malzemesi','bags_week','bag_g',F['LDPE']),('PET şişe gövdesi','bottles_week','bottle_g',F['PET'])]:
            count=v.get(count_key);weight=v.get(weight_key)
            add(label,'Plastik malzeme',count*52*weight/1000 if count is not None and weight is not None else None,ef)
        missing.append('Plastik atıkların toplanması ve bertarafı (malzeme üretimi hesabı dışında)')
    if v.get('bus')=='Evet':
        km=v.get('bus_km');factor=v.get('bus_factor')
        add('Toplu taşıma','Ulaşım',km*52 if km is not None and factor is not None and factor>0 else None,factor or 0)
    if v.get('food')=='Evet':
        meat=v.get('beef_kg')
        add('Sığır eti (küresel yaşam döngüsü ortalaması)','Beslenme',annualize(meat,'hafta'),F['beef'])
        missing.append('Diğer gıda türleri (yalnızca sığır eti hesaplandı)')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Kompost yapıyorum':
        z=v.get('zuruf_ton')
        if z is not None:
            # IPCC 2006 composting default factors, wet weight; CH4=4kg/t, N2O=0.24kg/t.
            # GWP100 AR6 CH4 biogenic=27.2, N2O=273. Only a separately labeled illustrative estimate.
            rows.append({'Faaliyet':'Kompost (genel IPCC yaklaşımı; tahmini)','Modül':'Züruf (tahmini)','kg CO₂e/yıl':round(z*(4*27.2+0.24*273),3)})
            missing.append('Kompost tahmini fındık zürufuna özgü değildir; toplamdan ayrı raporlanmalı')
        else:missing.append('Kompost miktarı (ton)')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Yakıyorum':
        z=v.get('zuruf_burn_kg');ef=v.get('zuruf_burn_ef')
        if z is not None and ef is not None and ef>0:
            rows.append({'Faaliyet':'Züruf yakma (kullanıcı faktörü; tahmini)','Modül':'Züruf (tahmini)','kg CO₂e/yıl':round(z*ef,3)})
        else:missing.append('Züruf yakma: doğrulanmış kg CO₂e/kg faktörü ve miktar gerekli')
    if v.get('farm')=='Evet' and v.get('zuruf')=='Bahçede bırakıyorum':missing.append('Bahçede bırakılan zürufun toprak emisyonları (ayrı yöntem gerekli)')
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
    """Optional private sheet storage; no success claims without an actual append."""
    try:
        cfg=st.secrets['connections']['gsheets']
        import gspread
        from google.oauth2.service_account import Credentials
        creds=Credentials.from_service_account_info(dict(cfg['service_account']),scopes=['https://www.googleapis.com/auth/spreadsheets'])
        ws=gspread.authorize(creds).open_by_key(cfg['spreadsheet_id']).worksheet('Yanitlar')
        ws.append_row([payload['id'],payload['timestamp'],json.dumps(payload['answers'],ensure_ascii=False),json.dumps(payload['results'],ensure_ascii=False)],value_input_option='RAW')
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
    select('heat','Eviniz genellikle nasıl ısınıyor?',['Doğalgaz','Kömür','Elektrik','Odun / fındık kabuğu','Diğer / bilmiyorum','Isınma yok'])
    if st.session_state.heat=='Doğalgaz':
        select('gas_mode','Doğalgaz tüketiminizi nasıl biliyorsunuz?', ['Aylık ortalama','Mevsime göre ayrı'])
        if st.session_state.gas_mode=='Mevsime göre ayrı':
            num('gas_winter','Kış aylarında ayda kaç m³ doğalgaz?',10)
            num('gas_other','Diğer aylarda ayda kaç m³ doğalgaz?',10)
        else:
            num('gas','Yılın 12 ayına göre ortalama aylık kaç m³ doğalgaz?',10)
            st.caption('Yalnızca kış faturasındaki tüketimi biliyorsanız mevsime göre ayrı seçeneğini kullanın.')
    if st.session_state.heat=='Kömür':num('coal','Bir kışta yaklaşık kaç kg kömür kullanıyorsunuz?',25)
    if st.session_state.heat=='Elektrik':st.caption('Elektrikli ısıtma evin toplam elektrik tüketimine dâhilse yeniden sayılmayacaktır.')
elif s==2:
    st.subheader('🚗 Günlük ulaşım')
    select('car','Özel araç kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.car=='Evet':
        select('fuel','Aracın yakıtı nedir?',['Benzin','Dizel','LPG','Elektrik','Bilmiyorum'])
        if st.session_state.fuel in ('Benzin','Dizel','LPG'):
            select('car_input','Hangisini bilmek daha kolay?',['Haftalık yakıt (litre)','Haftalık yol (km)','Bilmiyorum'])
            if st.session_state.car_input=='Haftalık yakıt (litre)':num('car_liters','Haftada yaklaşık kaç litre yakıt kullanıyorsunuz?',5)
            elif st.session_state.car_input=='Haftalık yol (km)':
                num('car_km','Haftada kaç km yol yapıyorsunuz?',10)
                num('car_rate','Aracınız 100 km’de kaç litre yakıyor?',0.5)
    st.markdown('#### 🏔️ Köy ve yayla yolları')
    select('road_type','En çok hangi yollarda araç kullanıyorsunuz?',
           ['Karışık yollar','Düz / sahil yolları','Yokuşlu köy / yayla yolları','Araç kullanmıyorum'])
    select('yayla_frequency','Köy veya yaylaya araçla ne sıklıkla gidiyorsunuz?',
           ['Ayda 1–2 kez','Hiç','Yılda birkaç kez','Haftada en az bir kez'])
    st.caption('Yokuşlar yakıt tüketimini etkileyebilir. Ancak gerçek tüketiminizi biliyorsanız bu etki zaten tüketiminizde bulunur; ek bir yokuş katsayısı uygulanmaz.')
    select('bus','Dolmuş / otobüs kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.bus=='Evet':
        num('bus_km','Haftada yaklaşık kaç km yolculuk yapıyorsunuz?',5)
        with st.expander('🔬 Toplu taşıma hesaplama ayarı (araştırmacı)'):
            st.caption('Doğrulanmış yolcu-km faktörünü girin; boşsa hesaplama yapılmaz. Dolmuş doluluk oranı sonucu etkiler.')
            num('bus_factor','kg CO₂e / yolcu-km',0.01)
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
            with st.expander('🔬 Yakma hesabı (araştırmacı)'):
                num('zuruf_burn_kg','Yılda kaç kg züruf yakılıyor?',10)
                num('zuruf_burn_ef','Kaynaklı emisyon faktörü (kg CO₂e/kg)',0.01)
                st.caption('Faktör doğrulanmadıkça emisyon toplamına eklenmez.')
    select('boat','Balıkçı teknesinin yakıtını siz mi karşılıyorsunuz?',['Hayır','Evet'])
    if st.session_state.boat=='Evet':
        select('boat_fuel','Teknenin yakıtı nedir?',['Dizel','Benzin','Bilmiyorum'])
        if st.session_state.boat_fuel!='Bilmiyorum':num('boat_liters','Haftada ortalama kaç litre yakıt kullanılıyor?',5)
elif s==4:
    st.subheader('♻️ Günlük alışkanlıklar')
    select('plastic','Plastik poşet veya PET şişe kullanıyor musunuz?',['Hayır','Evet'])
    if st.session_state.plastic=='Evet':
        num('bags_week','Haftada yaklaşık kaç poşet?',1)
        num('bottles_week','Haftada yaklaşık kaç PET şişe?',1)
        with st.expander('⚖️ Ürün ağırlıkları (isterseniz değiştirin)'):
            st.caption('Poşet ve şişe ağırlıkları kişiden kişiye değişir. Aşağıdaki değerler yalnızca örnek varsayımlardır.')
            st.number_input('Bir poşet kaç gram?',min_value=0.1,value=5.0,step=0.5,key='bag_g')
            st.number_input('Bir boş PET şişe gövdesi kaç gram?',min_value=0.1,value=20.0,step=1.0,key='bottle_g')
    select('food','Beslenme alışkanlığınızı araştırmada değerlendirmek ister misiniz?',['Hayır','Evet'])
    if st.session_state.food=='Evet':
        st.caption('Sığır eti için haftalık yaklaşık miktar yeterli. Diğer etleri aynı faktörle hesaplamıyoruz.')
        num('beef_kg','Haftada yaklaşık kaç kg sığır eti tüketiyorsunuz?',0.1)
    st.caption('Plastik malzeme üretimi ve sığır eti için kaynaklı yaklaşık hesaplar yapılır; diğer gıda ve atık işlemleri ayrı gösterilir.')
else:
    st.subheader('🌱 Karbon özetiniz')
    rows,missing=calculate();verified=[r for r in rows if '(tahmini)' not in r['Modül']];estimates=[r for r in rows if '(tahmini)' in r['Modül']];total=sum(r['kg CO₂e/yıl'] for r in verified)
    comparison=compare_models(rows)
    st.metric('Hesaplanabilen yıllık emisyon',f'{total:,.0f} kg CO₂e')
    st.caption('Bu bir **kısmi, varsayımlara dayalı emisyon tahminidir**; hesaplanamayan faaliyetler sıfır sayılmaz. Farklı yaşam döngüsü sınırları içeren bileşenler ayrı yorumlanmalıdır.')
    st.markdown('### 🌍 Genel referans ve 🌰 Eynesil kapsamı')
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
    st.caption(f'🏔️ Yerel ulaşım bilgisi: {road} · Köy/yayla yolculuğu: {yayla}. Doğrulanmamış eğim katsayısı uygulanmaz.')
    st.caption(f'🌦️ Yaşam bölgesi: {st.session_state.get("living_area","Belirtilmedi")} · Mevsimsel enerji durumu: {st.session_state.get("season_usage","Belirtilmedi")}. Mevsimlik tüketim girildiyse gerçek miktarlar kullanılır; iklim için keyfî çarpan uygulanmaz.')
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
                'Balıkçı teknesi':'Motor bakımı ve verimli seyir planlaması yakıt tüketimini azaltabilir.',
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
        st.write('Elektrik: Türkiye EVÇED 2023, 0,469 kg CO₂e/kWh. Yakıt: DESNZ 2026 doğrudan yanma referansları. Gübre: IPCC 2019 doğrudan N₂O EF₁=0,010 ve GWP100=273. Plastik: DESNZ 2025 birincil LDPE 2,96508 ve PET 3,86390 kg CO₂e/kg; örnek ağırlıklar kullanıcı tarafından değiştirilebilir. Sığır eti: Poore & Nemecek 2018 / Our World in Data küresel ortalama 99,48 kg CO₂e/kg ürün; yaşam döngüsü kapsamı yakıt faktörlerinden farklıdır. Kompost: IPCC 2006 genel 4 kg CH₄/t ve 0,24 kg N₂O/t yaş malzeme, yalnızca ayrı tahmin. Bu referanslar Eynesil ölçümü değildir. Toplu taşıma ve züruf yakma faktörleri doğrulanmış kaynakla araştırmacı tarafından girilmelidir.')
        if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    answers={k:v for k,v in st.session_state.items() if k not in ('sid','step','submitted') and not k.startswith('FormSubmitter') and k not in ('scenario_activity','scenario_pct')}
    payload={'id':st.session_state.sid,'timestamp':datetime.now(timezone.utc).isoformat(),'answers':answers,'results':{'total_kg':round(total,3),'activities':rows,'missing':missing,'estimate_only':estimates,'model_comparison':{'reference_kg':comparison['reference'],'eynesil_extended_kg':comparison['extended'],'local_activity_contribution_kg':comparison['increment'],'comparison_type':'scope_only_not_savings'}}}
    st.download_button('📥 Yanıtlarımı indir (JSON)',data=json.dumps(payload,ensure_ascii=False,indent=2,default=str),file_name='karbon_yanitim.json',mime='application/json',use_container_width=True)
    if st.session_state.get('consent'):
        if st.session_state.submitted:st.success('Yanıtınız araştırma tablosuna kaydedildi.')
        elif st.button('📤 Anonim yanıtımı araştırmaya gönder',type='primary',use_container_width=True):
            ok,err=send_sheet(payload)
            if ok:st.session_state.submitted=True;st.rerun()
            else:st.error('Kayıt yapılamadı. Araştırmacı Google Sheets bağlantısını henüz kurmamış olabilir. Yanıtlarınızı indirebilirsiniz.')
    else:st.caption('Araştırma izni verilmediğinden yanıtlarınız sunucuya gönderilmez.')

st.divider()
c1,c2=st.columns(2)
with c1:
    if st.button('← Geri',disabled=s==0,use_container_width=True):st.session_state.step-=1;st.rerun()
with c2:
    if st.button('Sonucumu gör 🌿' if s==4 else 'Devam et →',disabled=s==5,type='primary',use_container_width=True):st.session_state.step+=1;st.rerun()
