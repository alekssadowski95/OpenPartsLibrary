from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Enum
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

import uuid

class Base(DeclarativeBase):
  pass

class Part(Base):
    __tablename__ = 'parts'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False, default=str(uuid.uuid4()))
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
    cad_reference = Column(String(200))
    attached_documents_reference = Column(String(200))
    lead_time = Column(Integer)
    make_or_buy = Column(Enum('make', 'buy', name='make_or_buy_enum'))
    supplier = Column(String(100))
    manufacturer_number = Column(String(100))
    unit_price = Column(Numeric(10, 2))
    currency = Column(String(3))

    def __repr__(self):
        return f"<Part(id={self.id}, number={self.number}, name={self.name})>"

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NumberRange(Base):
    __tablename__ = 'number_ranges'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(String(1000))
    date_created = Column(DateTime, default=datetime.utcnow)

#Supplier model
class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False, default=str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="No description")                        
    street = Column(String(200))
    house_number = Column(String(20))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Supplier(id={self.id}, name={self.name}, city={self.city})>"
    
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    
