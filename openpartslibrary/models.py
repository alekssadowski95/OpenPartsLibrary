from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Part(Base):
    __tablename__ = 'parts'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    number = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000))
    revision = Column(String(10), default="1")
    lifecycle_state = Column(String(50), default="In Work")
    owner = Column(String(100))
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
    make_or_buy = Column(String(10))
    supplier = Column(String(100))
    manufacturer_number = Column(String(100))
    unit_price = Column(Numeric(10, 2))
    currency = Column(String(3))

    def __repr__(self):
        return f"<Part {self.part_number} - {self.part_name}>"

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
