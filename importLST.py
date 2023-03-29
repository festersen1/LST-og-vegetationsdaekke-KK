import ee
import geopandas as gpd
import pandas as pd
import geemap
from sqlalchemy import create_engine
import geojson
import os
import numpy as np
import json
from shapely import wkt


# Initialize GEE/GCLOUD
bydataemail = 'bydata.gcloud.import@gmail.com'
keyfile= r"C:\Users\hg4b\OneDrive - Københavns Kommune\coral-inverter-380112-a442db6523bb.json"
credentials = ee.ServiceAccountCredentials(email=bydataemail, key_file=keyfile)
ee.Initialize(credentials)


# ***************************************************
#    Defintion af områder der skal analyseres
# ***************************************************
# Navn på områder (bruges til tabel i prod)
nameSql = 'byudvik_raekkef_kp19'
# Navn på grupperingskollone
nameGroupCol = 'omraade'
# Connections til KGB
#Dist
dist_db_connection_url = "postgresql://kgb:kgb@kgb-dist-db01:5432/kgb"
con_dist = create_engine(dist_db_connection_url)

#Prod
prod_db_connection_url = "postgresql://postgres:}4YR]Gu\AAvCxJCS@kgb-prod-db01:5432/kgb_prod"
con_prod = create_engine(prod_db_connection_url)
#Områder
rois = """select wkb_geometry, obj_type, omraade,delomraade, id from okfkp19.overordnet_byudvikling_raekkefoelgeplan_kp19 where wkb_geometry is not null  and ST_isvalid(wkb_geometry)is true """
roisDF = gpd.GeoDataFrame.from_postgis(rois, con_dist, geom_col='wkb_geometry')
roisDF = geemap.geopandas_to_ee(roisDF)

omraadeGraense = roisDF



#ROI til filterbounds på imagecollections
roi =   ee.Geometry.Polygon([[[12.435873237304675, 55.725310214675666], [12.435873237304675, 55.610681528845866], [12.716024604492175, 55.610681528845866],  [12.716024604492175, 55.725310214675666]]]);

#*********************************************
#               Funktioner
#*********************************************
def createBands(image):
    # Beregner bands der anvendes til analysen
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    thermal = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(272.15).rename('LST')
    timeband = ee.Number(image.get('system:time_start'))
    image = image.addBands(ndvi).addBands(thermal).set('system_time_start', image.get('system:time_start')).set('Date', ee.Date(image.get('system:time_start')))
    return image

def createBandsL5(image):
    ndvi = image.normalizedDifference(['SR_B4', 'SR_B3']).rename('NDVI')
    thermal = image.select('ST_B6').multiply(0.00341802).add(149.0).subtract(272.15).rename('LST')
    timeband = ee.Number(image.get('system:time_start'))
    image = image.addBands(ndvi).addBands(thermal).set('system_time_start', image.get('system:time_start')).set('Date', ee.Date(image.get('system:time_start')))
    return image

def cleanUpAllLandsat(image):
  #Develop masks for unwanted pixels (fill, cloud, cloud shadow).
  qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
  saturationMask = image.select('QA_RADSAT').eq(0)
  # Replace original bands with scaled bands and apply masks.
  return image.updateMask(qaMask).updateMask(saturationMask)


# Zonal statistics. Beregnes med EE's funktion 'reduceRegions' hvor der beregnes et gennemsnit inden for hvert område for hvert billede
def setPropertyOmraader(image):
  dictio = image.select('LST','NDVI').reduceRegions(omraadeGraense ,ee.Reducer.mean())
  return dictio.set('dato', image.get('Date')).set('system_index_t', image.get('system:index'))

# Clean up: Beregner datokolonne og omdøber kolonner
def zonalStatsCleanUp(InputCollection):
    df = pd.json_normalize(InputCollection, "features")# Normalisererer inputtet fra zonal statistics (reduce regions) og laver det om til en pandas dataframe

    df['satellit']=df['id'].str.split('_',expand=True)[0] # Splitter ID'et på billedet og bruger stykke nr. 1 (nr. 0 i pythonrækkefølge) som sattelit
    df['datotekst']=df['id'].str.split('_',expand=True)[2] # Splitter ID'et og bruger stykke nr. 3 (nr. 2 i python) til at definere datoen

    df['dato'] = pd.to_datetime(df['datotekst']).dt.date # Caster datoteksten til en reel datotype

    df.rename(columns = {'properties.LST':'lst_mean','properties.omraade':'omraade','properties.omraade_navn':'omraade', 'properties.NDVI':'ndvi_mean', 'properties.navn':'omraade', 'properties.bydel_nr':'bydel_nr', 'properties.id':'id', 'geometry.type':'geometry_type', 'geometry.coordinates':'geometry_coordinates'}, inplace = True) #Omdøber kolonner
    return df

def pivotering(inputdf):
    # Laver pivotering pba. af år og deler områderne ud i rækker
    inputdf['aar'] = pd.DatetimeIndex(inputdf['dato']).year
    pivot_heleaaret = pd.pivot_table(inputdf, values='lst_mean', index=['aar'],
                    columns=['omraade'], aggfunc=np.mean)

    return pivot_heleaaret


#Definition af imagecollections:
landsat8_summer = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate('2013-06-01','2030-12-31').filter(ee.Filter.calendarRange(6, 8, 'month')).filter(ee.Filter.lt('CLOUD_COVER_LAND', 20)).filterBounds(omraadeGraense).map(createBands).map(cleanUpAllLandsat)
landsat9_summer = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate('2013-06-01','2030-12-31').filter(ee.Filter.calendarRange(6, 8, 'month')).filter(ee.Filter.lt('CLOUD_COVER_LAND', 20)).filterBounds(omraadeGraense).map(createBands).map(cleanUpAllLandsat)
landsat5_summer = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').filterDate('1983-06-01', '2013-12-31').filter(ee.Filter.calendarRange(6, 8, 'month')).filter(ee.Filter.lt('CLOUD_COVER_LAND', 20)).filterBounds(omraadeGraense).map(createBandsL5).map(cleanUpAllLandsat)

merged58 = landsat5_summer.merge(landsat8_summer)
inputLandsat_summer = merged58.merge(landsat9_summer)
#****************************************
#     Beregning af LST inden for områder
#****************************************
## Der laves beregninger af LST pr. område og data skrives til KGB
#   *** Sommer ***
## Områder
## Landsat 5
zonalOmraadel5_summer = landsat5_summer.map(setPropertyOmraader)
Omraadefcl5_summer = zonalOmraadel5_summer.flatten().getInfo()
dfomraadel5_summer =zonalStatsCleanUp(Omraadefcl5_summer)

## Landsat 8
zonalOmraadel8_summer = landsat8_summer.map(setPropertyOmraader)
Omraadefcl8_summer = zonalOmraadel8_summer.flatten().getInfo()
dfomraadel8_summer =zonalStatsCleanUp(Omraadefcl8_summer)

## Landsat 9
zonalOmraadel9_summer = landsat9_summer.map(setPropertyOmraader)
Omraadefcl9_summer = zonalOmraadel9_summer.flatten().getInfo()
dfomraadel9_summer =zonalStatsCleanUp(Omraadefcl9_summer)


dfomraade_summer = pd.concat([dfomraadel5_summer, dfomraadel8_summer, dfomraadel9_summer])
pivotomraade_summer = pivotering(dfomraade_summer)


dfomraade_summer.astype({'geometry_coordinates': 'string'}).dtypes
dfomraade_summer = dfomraade_summer.drop(columns=['geometry_coordinates', 'geometry_type'])

# Skriv til prod:
overfladetempsumName            =   'f_overfladetemp_sommer_'+nameSql
overflatetemp_aarliggnssumName  =   'f_overfladetemp_sommer_aarlig_'+nameSql

dfomraade_summer.to_sql(overfladetempsumName, con_prod, if_exists='replace',index=True,schema='dmi')
pivotomraade_summer.to_sql(overflatetemp_aarliggnssumName, con_prod, if_exists='replace',index=True,schema='dmi')
