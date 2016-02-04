# fascicle

Fascicle is a tool to help manage multiple tractography files for ease of data management. 

It's designed to ease the workflow with [ANTs normalization tool](http://stnava.github.io/ANTs/) for non-linear tractography deformations with large datasets. 

## Requirements

* numpy
* vtk
* sqlalchemy

## Install

```
    python setup.py install
```

## VTK file format
Fascicle import and export vtk files for tractography representation. 
It is capale of reading both .vtk ascii files and .vtp files. 

**Use .vtp for file import exports for scalar availability**

## Usage

Fascicle collections are sqlite databases, therefore they are compatible with any sqlite reader. 

**Create a new tractography collection**
```
trkmanage.py init -d collection.tdb -i input.vtk
```

**Add new tracts to existing collection**
```
trkmanage.py init -d existing.tdb -i addthis.vtk
```

**Export tracts as a merged file**
```
trkmanage.py expvtk -d existing.tdb --merged -o mergedtracts.vtp
```

**Export points as csv for ANTs**
```
trkmanage.py expcsv -d collection.tdb -o points_before.csv
```

Then the csv file can be used with ANTs with
```bash
antsApplyTransformToPoints -d 3 -i points_before.csv -o pointss_after.csv -t [Affine.mat,1] -t WarpInverse.nii.gz
```
Note that Point transforms in ANTs is the inverse of the desired transform direction. 

**Import ANTs deformed points back into the collection**
```
trkmanage.py tradd  -d collection.tdb -i points_after.csv -n mytransform -p "parameters I used"
```

**Export tracts with the newly transformed coordinates**
Find out the avaiable tracts and transforms
```
trkmanage.py list -d collection.tdb
```
Export specifics
```
trkmanage.py expvtk -d collection.tdb -t tractname -m mytransform -o aftertrans.vtp
```

