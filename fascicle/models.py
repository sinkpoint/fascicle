from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Tract(Base):
    __tablename__='tracts'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    group = Column(Integer)
    streamlines = relationship("Streamline", backref="tract")
    transform_set = relationship("TractTransforms", back_populates="tract")

class Streamline(Base):
    __tablename__='streamlines'
    id = Column(Integer, primary_key=True)
    tract_id = Column(Integer, ForeignKey('tracts.id'))
    point_set = relationship("StreamPoints", back_populates="streamline")

class Point(Base):
    __tablename__ = 'points'
    id = Column(Integer, primary_key=True)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    streamline_set = relationship("StreamPoints", back_populates="point")

class StreamPoints(Base):
    __tablename__='streampoints'
    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('streamlines.id'))
    point_id = Column(Integer, ForeignKey('points.id'))
    ord = Column(Integer)
    streamline = relationship("Streamline", back_populates="point_set")
    point = relationship("Point", back_populates="streamline_set")

class Scalar(Base):
    __tablename__='scalars'
    id = Column(Integer, primary_key=True)
    point_id = Column(Integer, ForeignKey('points.id'))
    name = Column(String)
    value = Column(Float)

class PointMapping(Base):
    __tablename__='point_mappings'
    id = Column(Integer, primary_key=True)
    orig_id = Column(Integer, ForeignKey('points.id'))
    result_id = Column(Integer, ForeignKey('points.id'))
    transform_id = Column(Integer, ForeignKey('transforms.id'))

    from_point = relationship("Point", foreign_keys=[orig_id], backref="transform_set")
    to_point = relationship("Point", foreign_keys=[result_id])

class Transform(Base):
    __tablename__='transforms'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    params = Column(String)
    tract_set = relationship("TractTransforms", back_populates="transform")

class TractTransforms(Base):
    __tablename__='tract_transforms'
    id = Column(Integer, primary_key=True)
    tract_id = Column(Integer, ForeignKey('tracts.id'))
    trans_id = Column(Integer, ForeignKey('transforms.id'))
    tract = relationship("Tract", back_populates="transform_set")
    transform = relationship("Transform", back_populates="tract_set")


