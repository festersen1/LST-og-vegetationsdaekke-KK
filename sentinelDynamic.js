var geometry = KK;
Map.centerObject(geometry);
var s2_before_coll = ee.ImageCollection('COPERNICUS/S2_SR')
     .filterDate('2019-07-01', '2019-08-01')
     .filterBounds(geometry)
     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10));
    // 2022-08-04
var s2_after_coll = ee.ImageCollection('COPERNICUS/S2_SR')
     .filterDate('2022-08-05', '2022-08-15')
     .filterBounds(geometry)
     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60));
     
var s2_before = s2_before_coll.mosaic().clip(geometry);
var s2_after = s2_after_coll.mosaic().clip(geometry);

var dw_before_coll = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
     .filterDate('2019-07-01', '2019-08-01')
     .filterBounds(geometry);
     
var dwVisParams = {
  min: 0,
  max: 8,
  palette: ['#419BDF', '#397D49', '#88B053', '#7A87C6',
    '#E49635', '#DFC35A', '#C4281B', '#A59B8F', '#B39FE1']
};

     
var dw_after_coll = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
     .filterDate('2022-08-05', '2022-08-15')
     .filterBounds(geometry);
     
var dw_before = dw_before_coll.mosaic().clip(geometry);
var dw_after = dw_after_coll.mosaic().clip(geometry);

var class_before = dw_before.select('label');
var class_after = dw_after.select('label');

Map.addLayer(s2_before,{bands:['B4','B3','B2'],min:0,max:3000},'S2_before');
Map.addLayer(s2_after,{bands:['B4','B3','B2'],min:0,max:3000},'S2_after');
Map.addLayer(class_before,dwVisParams,'LULC_before');
Map.addLayer(class_after,dwVisParams,'LULC_after');

var builtup_before = dw_before.select('built');
var builtup_after = dw_after.select('built');

var new_builtup = builtup_before.lt(0.25).and(builtup_after.gt(0.60));
var new_builtup = new_builtup.updateMask(new_builtup);

Map.addLayer(new_builtup,{min:0,max:1,palette:['white','red']},'new_builtup');

// var groent_til_byg = class_before.eq(1).or(class_before.eq(2)).or(class_before.eq(3)).or(class_before.eq(4)).or(class_before.eq(5)).and(class_after.eq(6));

var maskeaendringer = class_before.eq(1).or(class_before.eq(2)).or(class_before.eq(3)).or(class_before.eq(4)).or(class_before.eq(5)).and(class_after.eq(6));
var groent_til_byg = maskeaendringer.eq(1)

Map.addLayer(groent_til_byg,{min:0,max:1,palette:['white','red']},'Grønt til Byg');


Export.image.toDrive({
  image: groent_til_byg,
  description: 'groent_til_byg_19_22',
  maxPixels:9999999999,
  region: geometry
});



Export.image.toDrive({
  image: s2_before.select(['B8','B4','B3','B2']),
  description: 's2_before_19_22',
  maxPixels:9999999999,
  region: geometry
});

Export.image.toDrive({
  image: s2_after.select(['B8','B4','B3','B2']),
  description: 's2_after_19_22',
  maxPixels:9999999999,
  region: geometry
});



Export.image.toDrive({
  image: class_before,
  description: 'class_before_19_22',
  maxPixels:9999999999,
  region: geometry
});

Export.image.toDrive({
  image:class_after,
  description: 'class_after_19_22',
  maxPixels:9999999999,
  region: geometry
});

