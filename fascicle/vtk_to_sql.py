#!/usr/bin/env python
import vtk
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
import os    

def loadVtk(filename):
    if 'vtp' in filename:
        vreader = vtk.vtkXMLPolyDataReader()
    else:
        vreader = vtk.vtkPolyDataReader()

    vreader.SetFileName(filename)
    vreader.Update()
    polydata = vreader.GetOutput()

    streamlines = []
    verts = vtk_to_numpy(polydata.GetPoints().GetData())
    scalars = polydata.GetPointData().GetScalars()
    if scalars is not None:
        scalars = vtk_to_numpy(scalars)

    for i in range(polydata.GetNumberOfCells()):
        pids =  polydata.GetCell(i).GetPointIds()
        ids = [ pids.GetId(p) for p in range(pids.GetNumberOfIds())]
        streamlines.append(ids)


    return {'points':verts, 'values':scalars, 'streamlines':streamlines}


TRACT_TABLE_SQL = """

DROP TABLE IF EXISTS `points`;
        
CREATE TABLE `points` (
  `id` INTEGER PRIMARY KEY,
  `x` DOUBLE NOT NULL DEFAULT 0,
  `y` DOUBLE NOT NULL DEFAULT 0,
  `z` DOUBLE NOT NULL DEFAULT 0
);


DROP TABLE IF EXISTS `streamlines`;
        
CREATE TABLE `streamlines` (
  `id` INTEGER PRIMARY KEY,
  `stream_id` INTEGER NOT NULL DEFAULT 0,
  `point_id` BIGINT NOT NULL DEFAULT NULL,
  `ord` BIGINT NOT NULL DEFAULT 0,
  `tracts_id` INTEGER NULL DEFAULT NULL
);



DROP TABLE IF EXISTS `values`;
        
CREATE TABLE `values` (
  `id` INTEGER PRIMARY KEY,
  `point_id` BIGINT NOT NULL DEFAULT NULL,
  `type` VARCHAR(32) NOT NULL,
  `value` FLOAT NULL DEFAULT NULL
);



DROP TABLE IF EXISTS `tracts`;
        
CREATE TABLE `tracts` (
  `id` INTEGER PRIMARY KEY,
  `name` VARCHAR(128) NULL DEFAULT NULL,
  `path` VARCHAR(256) NULL DEFAULT NULL
);

"""
def tracts_to_db(filename, dbname, tract_name=None):
    global TRACT_TABLE_SQL

    vdata = loadVtk(filename)

    is_db_exist = False

    if tract_name is None:
        tract_name = os.path.basename(filename)

    if os.path.isfile(dbname):
        is_db_exist = True

    tract_full_path = os.path.abspath(filename)

    import sqlite3
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    if not is_db_exist:
        #qry = open('tract_tables.sql').read()
        c.executescript(TRACT_TABLE_SQL)

    q = 'insert into tracts(name, path) values ("%s","%s");' % (tract_name, tract_full_path)
    c.execute(q)
    tract_id = c.lastrowid

    for i,p in enumerate(vdata['points']):
        q = 'insert into points(id, x,y,z) values (%d,%f,%f,%f);' % (i,p[0],p[1],p[2])
        print q
        c.execute(q)
    id_delta = c.lastrowid - len(vdata['points']) -1

    if vdata['values'] is not None:
        for vi, vd in enumerate(vdata['values']):
            vid = vi+id_delta
            q = 'insert into `values` (point_id, type, value) values (%d, "%s", %f)' % (vid, 'scalar', vd)
            print q
            c.execute(q)

    for si, sd in enumerate(vdata['streamlines']):
        for pi, pd in enumerate(sd):
            pid = pd+id_delta
            q = 'insert into streamlines(stream_id, point_id, ord, tracts_id) values(%d, %d, %d, %d)' % (si, pid, pi, tract_id)
            print q
            c.execute(q)            

    conn.commit()
    c.close()
    conn.close()





def main(filename, dbname):
    tracts_to_db(filename, dbname)


if __name__ == '__main__':
    import sys
    main(sys.argv[1], sys.argv[2])