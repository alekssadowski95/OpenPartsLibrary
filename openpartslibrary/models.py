from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Enum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
  pass

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    part_id = Column(ForeignKey('parts.id'))
    part = relationship('Part', back_populates='cad_reference')


class Part(Base):
    __tablename__ = 'parts'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    number = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="No description")
    revision = Column(String(10), default="1")
    lifecycle_state = Column(String(50), default="In Work")
    owner = Column(String(100), default="system")
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    material = Column(String(100))
    mass = Column(Float)
    dimension_x = Column(Float)
    dimension_y = Column(Float)
    dimension_z = Column(Float)
    quantity = Column(Integer, default=0)
    attached_documents_reference = Column(String(200))
    lead_time = Column(Integer)
    make_or_buy = Column(Enum('make', 'buy', name='make_or_buy_enum'))
    manufacturer_number = Column(String(100))
    unit_price = Column(Numeric(10, 2))
    currency = Column(String(3))

    cad_reference = relationship('File', back_populates='part', uselist=False)

    supplier_id = Column(ForeignKey('suppliers.id'))
    supplier = relationship('Supplier', back_populates='parts')

    def __repr__(self):
        return f"<Part(id={self.id}, number={self.number}, name={self.name})>"

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    
class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="No description")                        
    street = Column(String(200))
    house_number = Column(String(20))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parts = relationship(Part)

    
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

class Adress(Base):
    __tablename__ = 'adresses'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    street = Column(String(200))
    house_number = Column(String(20))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    
class Component(Base):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)


'''
Relationship tables
'''
class ComponentComponent(Base):
    __tablename__ = 'component_component'

    id = Column(Integer, primary_key=True)

class PartSupplier(Base):
    __tablename__ = 'part_supplier'

    id = Column(Integer, primary_key=True)

class PartFile(Base):
    __tablename__ = 'part_file'

    id = Column(Integer, primary_key=True)

class SupplierAdress(Base):
    __tablename__ = 'supplier_adress'

    id = Column(Integer, primary_key=True)

class SupplierFile(Base):
    __tablename__ = 'supplier_file'

    id = Column(Integer, primary_key=True)



    
