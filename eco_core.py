
"""Eco-Algoritma V18: deterministic partial-emission model; reference assumptions not local measurements."""
from math import isfinite

FACTORS = {'electric':0.469,'gas':2.02633,'coal':2.90495,'Benzin':2.075,'Dizel':2.58354,'LPG':1.55713,'bag':2.96508}
BIO_CH4, BIO_N2O, GWP_CH4, GWP_N2O = 300.,4.,28.,265.
WOOD_NCV, SHELL_NCV = 15.6,19.10
PET_RECYCLING, PET_LANDFILL = -1.04,0.02

def biomass_factor(ncv):
    return ncv*(BIO_CH4*GWP_CH4+BIO_N2O*GWP_N2O)/1_000_000

def validate(d):
    for k,v in d.items():
        if isinstance(v,(int,float)) and (not isfinite(v) or v<0):
            raise ValueError(f'{k}: negatif veya sonlu olmayan değer')
    if d['bus_occupancy']<1: raise ValueError('Minibüs yolcu sayısı en az 1 olmalı')
    if d['fertilizer_n_fraction']>1: raise ValueError('Gübre azot oranı 0-1 aralığında olmalı')
    if d['fertilizer_ef_n2o']>1: raise ValueError('N₂O-N oranı 0-1 aralığında olmalı')
    if d['car_fuel'] not in ('Benzin','Dizel','LPG') or d['boat_fuel'] not in ('Benzin','Dizel'):
        raise ValueError('Geçersiz yakıt türü')

def calculate(d, f=FACTORS):
    validate(d)
    p={
      'Elektrik':d['electric_kwh']*f['electric'],
      'Doğalgaz':d['gas_m3']*f['gas'],
      'Kömür':d['coal_kg']*f['coal'],
      'Özel araç':d['car_liters']*f[d['car_fuel']],
      'Minibüs (kişi payı)':d['bus_passenger_km']*d['bus_l100']/100/d['bus_occupancy']*f['Dizel'],
      'Plastik poşet (malzeme)':d['bag_count']*d['bag_g']/1000*f['bag'],
      'Odun (CH₄+N₂O)':d['wood_kg']*biomass_factor(WOOD_NCV),
      'Fındık kabuğu (CH₄+N₂O)':d['shell_kg']*biomass_factor(SHELL_NCV),
      'Tekne yakıtı':d['boat_l_week']*d['boat_weeks']*f[d['boat_fuel']],
      'Gübre (doğrudan N₂O)':d['fertilizer_bags']*d['fertilizer_bag_kg']*d['fertilizer_n_fraction']*d['fertilizer_ef_n2o']*(44/28)*GWP_N2O,
    }
    base_keys=list(p)[:6]
    base=sum(p[k] for k in base_keys)
    expanded=sum(p.values())
    local=expanded-base
    return {'parts':p,'base':base,'expanded':expanded,'local':local,'local_percent':local/expanded*100 if expanded>0 else None}

def scenario(d, electricity=0,car=0,bags=0,heating=0):
    for x in (electricity,car,bags,heating):
        if not 0<=x<=100: raise ValueError('Azaltım yüzdesi 0-100 aralığında olmalı')
    d2=d.copy()
    d2['electric_kwh']*=1-electricity/100
    d2['car_liters']*=1-car/100
    d2['bag_count']*=1-bags/100
    for k in ('gas_m3','coal_kg','wood_kg','shell_kg'):
        d2[k]*=1-heating/100
    old,new=calculate(d),calculate(d2)
    return {'current':old['expanded'],'alternative':new['expanded'],'difference':old['expanded']-new['expanded'],'percent':(old['expanded']-new['expanded'])/old['expanded']*100 if old['expanded'] else None}

def pet_scenario(monthly_count,grams):
    if min(monthly_count,grams)<0: raise ValueError('Negatif PET girdisi')
    return monthly_count*12*grams/1000/907.18474*(PET_LANDFILL-PET_RECYCLING)*1000

DEFAULT={'electric_kwh':2400.,'gas_m3':0.,'coal_kg':0.,'wood_kg':0.,'shell_kg':0.,'car_liters':0.,'car_fuel':'Benzin','bus_passenger_km':0.,'bus_l100':0.,'bus_occupancy':8.5,'bag_count':208.,'bag_g':5.,'boat_l_week':0.,'boat_weeks':0.,'boat_fuel':'Dizel','fertilizer_bags':0.,'fertilizer_bag_kg':50.,'fertilizer_n_fraction':0.20,'fertilizer_ef_n2o':0.010}
