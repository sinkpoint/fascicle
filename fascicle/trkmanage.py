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
    polydata.ReleaseDataFlagOn()

    streamlines = []
    verts = vtk_to_numpy(polydata.GetPoints().GetData())
    scalars = {}

    pointdata = polydata.GetPointData()
    for si in range(pointdata.GetNumberOfArrays()):
        sname =  pointdata.GetArrayName(si)
        scalars[sname] = vtk_to_numpy(pointdata.GetArray(si))

    for i in range(polydata.GetNumberOfCells()):
        pids =  polydata.GetCell(i).GetPointIds()
        ids = [ pids.GetId(p) for p in range(pids.GetNumberOfIds())]
        streamlines.append(ids)

    res = {'points':verts, 'values':scalars, 'streamlines':streamlines}
    return res

def saveVtk(dataset, filename):
    polydata = vtk.vtkPolyData()
    points = vtk.vtkPoints()
    lines = vtk.vtkCellArray()

    points.SetNumberOfPoints(len(dataset['points']))
    for i,p in enumerate(dataset['points']):
        #print p
        points.SetPoint(i,p[0],p[1],p[2])

    for stream in dataset['streams']:
        lines.InsertNextCell(len(stream))
        for i in stream:
            lines.InsertCellPoint(i)

    polydata.SetPoints(points)
    polydata.SetLines(lines)

    pointdata = polydata.GetPointData()
    for i in  dataset['values']:
        print i,len(dataset['values'][i])
    for sname, sarr in dataset['values'].iteritems():
        arr = vtk.vtkFloatArray()
        arr.SetName(sname)
        arr.SetNumberOfComponents(1)
        for v in sarr:
            arr.InsertNextTuple1(v)
        pointdata.AddArray(arr)
        pointdata.SetActiveScalars(sname)


    print len(dataset['streams']),'streamlines, ',len(dataset['points']),' points.'

    if 'vtp' in filename:
        vreader = vtk.vtkXMLPolyDataReader()
        vwriter = vtk.vtkXMLPolyDataWriter()
    else:
        vreader = vtk.vtkPolyDataReader()
        vwriter = vtk.vtkPolyDataWriter()

    if os.path.isfile(filename):
        print '{} exists, appending to it'.format(filename)
        vreader.SetFileName(filename)
        vreader.Update()
        old_polydata = vreader.GetOutput()
        old_polydata.ReleaseDataFlagOn()
        appendfilter = vtk.vtkAppendFilter()
        appendfilter.AddInput(old_polydata)
        appendfilter.AddInput(polydata)
        appendfilter.Update()

        gfilter = vtk.vtkGeometryFilter()
        gfilter.SetInput(appendfilter.GetOutput())
        polydata = gfilter.GetOutput()
        polydata.ReleaseDataFlagOn()


    vwriter.SetInput(polydata)
    vwriter.SetFileName(filename)
    vwriter.Write()
    print 'saved',filename




from models import *
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.expression import func
from sqlalchemy.sql import exists
import csv

class TrackManager():
    def __init__(self, dbname = 'tracts.db'):
        self.dbname = dbname
        self.engine = None
        self.session = scoped_session(sessionmaker())

    def init_db(self):
        dbname = 'sqlite:///'+self.dbname
        self.engine = create_engine(dbname, echo=False)
        self.session.remove()
        self.session.configure(bind=self.engine, autoflush=False, expire_on_commit=False)
        #Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def tracts_to_db(self, filename, tract_name=None, group=None):
        vdata = loadVtk(filename)

        self.init_db()

        if tract_name is None:
            tract_name = os.path.basename(filename)

        tract_full_path = os.path.abspath(filename)

        q = self.session.query(exists().where(Tract.name==tract_name)).scalar()
        if q:
            print 'Tract %s already exists, skipping.' % (tract_name)
            return



        print 'insert tract '+tract_name
        new_tract = Tract(name=tract_name, path=tract_full_path, group=group)
        self.session.add(new_tract)
        self.session.commit()

        tract_id = new_tract.id


        id_delta = self.session.query(func.max(Point.id)).first()[0]

        if id_delta is None:
            id_delta = 0
        else:
            id_delta += 1

        queue = []
        for i,p in enumerate(vdata['points']):
            queue.append({'id':i+id_delta, 'x':p[0], 'y':p[1], 'z':p[2]})

        if len(queue) > 0:
            print 'insert {} points'.format(len(queue))
            self.engine.execute(Point.__table__.insert(), queue)

        if vdata['values'] is not None and len(vdata) > 0:
            queue = []
            for sname, varr in vdata['values'].iteritems():
                print 'insert scalar set {}'.format(sname)
                if len(varr) > 0 and type(varr[0]) is np.ndarray:
                    print 'Skip {}: is ndarray'.format(sname)
                    # skip tensor data for now
                    # [todo] add tensor data compatibility
                    continue

                for vi, val in enumerate(varr):
                    vid = vi+id_delta                   
                    queue.append({'point_id':vid, 'name':sname, 'value':val})
            
            if len(queue) > 0:                    
                self.engine.execute(Scalar.__table__.insert(), queue)


        sid_delta = self.session.query(func.max(Streamline.id)).first()[0]

        if sid_delta is None:
            sid_delta = 0
        else:
            sid_delta += 1

        queue = []
        stm_queue = []
        for si, sd in enumerate(vdata['streamlines']):
            sid = si+sid_delta
            stm_queue.append({'id':sid, 'tract_id':tract_id})
            for pi, pd in enumerate(sd):
                pid = pd+id_delta
                queue.append({'stream_id':sid, 'point_id':pid, 'ord':pi})

        if len(stm_queue) > 0:
            self.engine.execute(Streamline.__table__.insert(), stm_queue)
            print 'insert {} streamlines'.format(len(stm_queue))

        if len(queue) > 0:
            self.engine.execute(StreamPoints.__table__.insert(), queue)

        # conn.commit()
        # c.close()
        # conn.close()
    def to_csv(self, csvfile, tract_name=None):
        """
            Output to ANTs compatible points in LPS space, assumes points are in RAS space. 
        """
        self.init_db()
        with open(csvfile,'wb') as fp:
            fp.write('x,y,z,t,label\n')
            points = self.session.query(Point).all()
            for p in points:
                fp.write('%f,%f,%f,0,%d\n' % (p.x*-1,p.y*-1,p.z,p.id))

    def list_tracts(self):
        self.init_db()
        tracts = self.session.query(Tract).all()
        for trk in tracts:
            print trk.id,'\t', trk.name

            print 'Tranforms:'
            for t in trk.transform_set:
                print '\t',t.id, t.transform.name

    def to_vtk(self, output='.', tract_name=None, trans_name=None, merged=False):
        self.init_db()
        q = self.session.query(Tract)
        trk_q = self.session.query(Tract.id, Tract.name, Tract.group)
        if tract_name is None:
            tracts = trk_q.all()
        else:
            tracts = trk_q.filter(Tract.name==tract_name)


        if trans_name is not None:
            trans_id = self.session.query(Transform.id).filter(Transform.name==trans_name).first()[0]

        dataset = {'points':[], 'values':{}, 'streams':[]}     
        p_idx = 0   
        for trk_id, trk_name, trk_grp in tracts:
            print '#TRACT',trk_id,trk_name,trk_grp
            if not merged:
                dataset = {'points':[], 'values':{}, 'streams':[]}

            streams = (self.session.query(Streamline, StreamPoints.ord, Point, Scalar.name, Scalar.value)
                        .join(StreamPoints, StreamPoints.stream_id == Streamline.id)
                )
            if trans_name is not None:
                streams = (
                    streams
                        .join(PointMapping, PointMapping.orig_id == StreamPoints.point_id)
                        .join(Point, Point.id == PointMapping.result_id)
                        .join(Scalar, Scalar.point_id == PointMapping.orig_id)
                        .filter(PointMapping.transform_id==trans_id)
                )   
            else:
                streams = (streams.join(Point, Point.id == StreamPoints.point_id)
                            .join(Scalar, Scalar.point_id == Point.id)
                )

            streams = streams.filter(Streamline.tract_id==trk_id)

            stm_buf = []
            last_stm_idx = -1
            last_p_idx = -1
            if not merged:
                p_idx = 0
                
            for stm,k,point, sname, svalue in streams:
                #print stm.id, point.x,point.y,point.z

                if stm.id != last_stm_idx and len(stm_buf) > 0:
                    dataset['streams'].append(stm_buf)
                    stm_buf = []

                if point.id != last_p_idx:
                    stm_buf.append(p_idx)
                    dataset['points'].append([point.x,point.y,point.z])
                    p_idx += 1

                    # add unique point data only when new point is created

                                    # save point and track ids to merged tracks for backprojection
                    if merged:
                        if 'pid' not in dataset['values']:
                            dataset['values']['pid'] = []
                        dataset['values']['pid'].append(point.id)

                        if 'tid' not in dataset['values']:
                            dataset['values']['tid'] = []
                        dataset['values']['tid'].append(stm.tract_id)

                        if 'group' not in dataset['values']:
                            dataset['values']['group'] = []
                        dataset['values']['group'].append(trk_grp)

                if sname not in dataset['values']:
                    dataset['values'][sname] = []
                dataset['values'][sname].append(svalue)



                last_stm_idx = stm.id
                last_p_idx = point.id

            file_out = output
            if not merged:
                if tract_name is not None:
                    file_out = output
                else:                
                    mypath = os.path.abspath(output)
                    base = os.path.basename(output).split('.')[0]
                    fname = '_'.join((base, trk_name, trans_name)) + '.vtp'
                    file_out = os.path.join(mypath, fname)

            saveVtk(dataset, file_out)

    def add_transformed(self, csvfile, name=None, param=None):
        """
            Import deformed point coordinates from ANTs to image
            Assumes LPS->RAS conversion. 
        """
        self.init_db()

        new_trans = Transform(name=name, params=param)
        self.session.add(new_trans)
        self.session.commit()

        trans_id = new_trans.id

        id_delta = self.session.query(func.max(Point.id)).first()[0]

        if id_delta is None:
            id_delta = 0
        else:
            id_delta += 1

        print 'insert new points'
        point_queue = []
        mapping_queue = []
        with open(csvfile, 'rb') as fp:
            preader = csv.DictReader(fp)
            for i,r in enumerate(preader):
                pid = i+id_delta
                point_queue.append({'id':pid, 'x':float(r['x'])*-1, 'y':float(r['y'])*-1, 'z':float(r['z'])})
                mapping_queue.append({'orig_id':r['label'], 'result_id':pid, 'transform_id':trans_id})

        self.engine.execute(Point.__table__.insert(), point_queue)
        self.engine.execute(PointMapping.__table__.insert(), mapping_queue)


    def sync_tract_transforms(self):
        all_trans_tract_q = (self.session
                .query(PointMapping.transform_id.label('trans_id'), Streamline.tract_id.label('tract_id'))
                .join("from_point", "streamline_set", "streamline")
                .distinct(PointMapping.transform_id, Streamline.tract_id)
                )

        existing = self.session.query(TractTransforms.trans_id, TractTransforms.tract_id)


        # print "dynamic"
        # for i,j in all_trans_tract_q.all():
        #     print i,j

        q = all_trans_tract_q.except_(existing)
        print "to add"
        for i,j in q.all():
            print i,j      
            self.session.add( TractTransforms(trans_id=i, tract_id=j) )
        self.session.commit()




TRKMGR = None

def list_cmd(args):
    dbname = args.d

    TRKMGR = TrackManager(dbname)
    TRKMGR.list_tracts()

def import_cmd(args):
    print 'import cmd'
    print args

    filename = args.i
    dbname = args.d
    group_id = args.group

    if dbname is None:
        dbname = os.path.basename(filename).split('.')[0]+'.tdb'
        print dbname

    TRKMGR = TrackManager(dbname)
    TRKMGR.tracts_to_db(filename, group=group_id)

def expcsv_cmd(args):
    print 'export to csv'
    print args

    dbname = args.d
    trkname = args.t
    csvfile = args.o
    if csvfile is None:
        csvfile = 'out.csv'
    TRKMGR = TrackManager(dbname)
    TRKMGR.to_csv(csvfile, tract_name=trkname)

def expvtk_cmd(args):
    print 'export to vtk'
    print args
    dbname = args.d
    vtkfile = args.o

    if vtkfile is None:
        vtkfile = 'tract'

    print 'save to vtkfile'
    TRKMGR = TrackManager(dbname)
    TRKMGR.to_vtk(vtkfile, tract_name=args.t, trans_name=args.m, merged=args.merged)

def tradd_cmd(args):
    print 'add transformed set'
    print args
    dbname = args.d
    csvfile = args.i

    TRKMGR = TrackManager(dbname)
    TRKMGR.add_transformed(csvfile, name=args.n, param=args.p)
    TRKMGR.sync_tract_transforms()

def main():
    import sys
    import argparse
    parser_shared = argparse.ArgumentParser(add_help=False)
    # base level arguments, for quick conversion
    parser_shared.add_argument('-d', metavar='dbfile', help='Tract db file')
    parser_shared.add_argument('-i', metavar='input file', help='Input file')


    parser = argparse.ArgumentParser(description='Tract db manager', parents=[parser_shared])
    subparser = parser.add_subparsers(title='actions')
    # functions needed:
    # add tract
    # export tract to csv
    # import deformed tracts
    # list tracts
    # delete tracts

    init_pars = subparser.add_parser('init', help='Create a new tract db', parents=[parser_shared])
    init_pars.add_argument('--group', help='Group ID this track belongs to')
    init_pars.set_defaults(func=import_cmd)

    tradd_pars = subparser.add_parser('tradd', help='Add transformed points from ANTs csv', parents=[parser_shared])
    tradd_pars.add_argument('-n', metavar='name', help='Name of this transformed set')
    tradd_pars.add_argument('-p', metavar='parameters', help='Comments for the parameters used')
    tradd_pars.set_defaults(func=tradd_cmd)

    list_pars = subparser.add_parser('list', help='List available tracts', parents=[parser_shared])
    list_pars.set_defaults(func=list_cmd)

    expcsv_pars = subparser.add_parser('expcsv',  parents=[parser_shared], help='Export points to ANTs compatible csv format')
    expcsv_pars.add_argument('-t', metavar='tract name')
    expcsv_pars.add_argument('-o', metavar='csv file', help='output file name')
    expcsv_pars.set_defaults(func=expcsv_cmd)

    expvtk_pars = subparser.add_parser('expvtk', parents=[parser_shared], help='Export tracts to vtk files')
    expvtk_pars.add_argument('-t', metavar='name')
    expvtk_pars.add_argument('-m', metavar='transform')
    expvtk_pars.add_argument('--merged', '-g', action='store_true', help='Output all tracts as one merged file, this overrides -t')
    expvtk_pars.add_argument('-o', help='Output file, valid ext: .vtk, .vtp')
    expvtk_pars.set_defaults(func=expvtk_cmd)

    args = parser.parse_args()
    args.func(args)
