# Import af plugins
import rasterio, os, numpy as np, rasterio.mask
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.plot import show
from rasterstats import zonal_stats
import fiona
from shapely import wkt
from shapely.geometry import MultiPolygon, shape, mapping, Polygon,box
import json
import sys
from osgeo import gdal, gdal_array,ogr
import subprocess
import psycopg2 as ps
import geopandas as gdp

#**************************************
#       Grundlæggende informationer
#**************************************
aar = '2019'        # Bruges til navngivning
dato = '13-06-2019' # Bruges til navngivning
slicingvalue = 0.3  #Slicingværdi til NDVI
redband = 3         # Nummer på rødt bånd
nirband = 4         # Nummer på NIR bånd

#**************************************
#         Stier og navngivning
#**************************************
## ****** OBS: her skal der rettes stier *******
# Main path til reclassificerede billeder - det er her de klassificerede billeder til NDVI havner:
path_to_main_folder = r"2019"

# Sti til den mappe, hvor zonal statistics skal havne:
path_to_zonals = r"Zonals"

# *** Shapefiler ***
## OBS: Husk at ret attributter, hvis lagene ændres. Der skal være en kolonne med NULL værdier i søerne og et areal i bydelene.
# Søer og vandløb mm. der skal brændes i raster
##shp = r"\soer_til_null_raster.shp"

#Shapefiler med bydele og kvarterer HUSK gamle bydele, hvis der bruges gamle satellitbilleder
bydele = r"bydele.shp"
kvarterer = r"kvarterer.shp"

# Rå rasterfil med RGBN-værdier:
# OBS: HUSK at projektion er UTM zone 32/ESPG:25832
input_raster = r"WorldView_2019_05062019_klip_modified_v8.tif"


# Nedenfor bliver diverse navne til outputfiler dannet:
# *** Reklassificering ***
# Parametre til navngivning
ndvi_name         = "output_ndvi_raw_"+ aar +".tif"
reclass_name      = "output_ndvi_sliced_reclassed_"+ aar +".tif"

ndvi_out_name     = os.path.join(path_to_main_folder,ndvi_name)
output_reclassified  = os.path.join(path_to_main_folder,reclass_name)

# *** Zonal stats ***
# Navne på outputs til zonal statistics. De bliver automatisk navngivet efter året.
navn_bydele_shp         = "zonal_stats_bydele_"+ aar +".shp"
navn_kvarterer_shp      = "zonal_stats_kvarterer_"+ aar +".shp"
navn_excel              = "zonal_stats_bydele_"+ aar +"_excel.xlsx"

zonal_stats_bydele_shp     = os.path.join(path_to_zonals,navn_bydele_shp)
zonal_stats_kvarterer_shp  = os.path.join(path_to_zonals,navn_kvarterer_shp)
zonal_excel                = os.path.join(path_to_zonals,navn_excel)

# Nedenstående laver mapperne, hvis den ikke eksisterer
if not os.path.exists(path_to_main_folder):
    os.makedirs(path_to_main_folder)
if not os.path.exists(path_to_zonals):
    os.makedirs(path_to_zonals)

#**************************************
#          Beregning af NDVI
#**************************************
with rasterio.open(input_raster) as dataset:
    datasetMetadata = dataset.meta.copy()
    # print(datasetMetadata)
    np.seterr(divide='ignore', invalid='ignore')

    band3 = dataset.read(redband) # Red band
    band4 = dataset.read(nirband) # NIR band
    ndvi = (band4- band3) / (band4 + band3)

    band3 = ""
    band4 = ""

    array = dataset.read()

    # Opdater metadata til båndet
    kwargs = datasetMetadata
    kwargs.update(
    dtype=rasterio.float32,
    count=1,
    compress='lzw')

    # Skriver NDVI til fil
    with rasterio.open(ndvi_out_name, 'w', **kwargs) as ndvidst:
        ndvidst.write_band(1, ndvi.astype(rasterio.float32))
    print('NDVI skrevet')

    # Fjerner alle celler med NDVI under 0,5
    slicingvalue_int = slicingvalue *100 # Ganges med 100 for at kunne bruges i nedenstående formel
    binary_ndvi = ndvi * 100
    binary_ndvi = np.where(binary_ndvi > slicingvalue_int, binary_ndvi,0.0)

    # Skriver ndvi > 0,5 til fil
    binary_ndvi = binary_ndvi * 0.01

    #Reklassificer, så alle celler med vegetation er 1
    data = 1*(binary_ndvi>=slicingvalue)

    # Skriv til ny fil og sæt 0 til nodata
    with rasterio.open(output_reclassified, 'w',height=ndvi.shape[0], width=ndvi.shape[1],dtype=ndvi.dtype, driver='GTiff',count=1, transform=datasetMetadata['transform'], crs=datasetMetadata['crs'], nodata=0) as reclass:
        reclass.write(data, 1)
    print('Reclassified skrevet')

    # Brænd søer og vandlønb ned i raster (pt udkommenteret)
##    mb_v = ogr.Open(shp)
##    mb_l = mb_v.GetLayer()
##
##    raster = gdal.Open(output_reclassified,gdal.GA_Update)
##    gdal.RasterizeLayer(raster, [1], mb_l, options=["ATTRIBUTE=DN"]) # Overskriver filen med det reclassificerede
##    raster = None
##    print('Søer brændt')
    # Luk datasæt
    ndvidst.close()
    dataset.close()
    reclass.close()

#**************************************
#         Zonal statistics
#**************************************
# Grænseværdi bliver skrevet i exceloutputtet
graensevaerdi = str(slicingvalue)
graensevaerdi = graensevaerdi.replace('.',',')

zs_byd = zonal_stats(bydele, output_reclassified, stats='count',geojson_out=True)
gdf_zs_byd =  gdp.GeoDataFrame.from_features(zs_byd)
gdf_zs_byd['andel'] = (gdf_zs_byd['count']*0.5*0.5)/gdf_zs_byd['areal_m2']*100
gdf_zs_byd['areal_groent'] = gdf_zs_byd['count']*0.5*0.5
gdf_zs_byd=gdf_zs_byd.set_crs('epsg:25832')

## Add new fields
gdf_zs_byd['dato'] = dato
gdf_zs_byd['graensevaerdi'] =slicingvalue
gdf_zs_byd['antal_beboere'] = 0 # Anvendes til at beregne grønt pr beboer - data indsættes manuelt senere

# Export to shapefile og excel
gdf_zs_byd.to_file(zonal_stats_bydele_shp)
## Fjern geom kolonne og eksporter til excel
gdf_zs_byd.drop(columns=['geometry'])
gdf_zs_byd.to_excel(zonal_excel)

print('ZS bydele lavet')


zs_kvart = zonal_stats(kvarterer, output_reclassified, stats='count',geojson_out=True)
gdf_zs_kvart =  gdp.GeoDataFrame.from_features(zs_kvart)
gdf_zs_kvart['andel'] = (gdf_zs_kvart['count']*0.5*0.5)/gdf_zs_kvart['areal_m2']*100

gdf_zs_kvart=gdf_zs_kvart.set_crs('epsg:25832')
# Export to shapefile
gdf_zs_kvart.to_file(zonal_stats_kvarterer_shp)
print('ZS kvarterer lavet')

print('***Done***')




