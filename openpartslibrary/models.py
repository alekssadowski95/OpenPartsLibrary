from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship, backref
from datetime import datetime


class Base(DeclarativeBase):
  pass

class ComponentComponent(Base):
    __tablename__ = 'component_component'

    id = Column(Integer, primary_key=True)

    parent_component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    child_component_id = Column(Integer, ForeignKey("components.id"), nullable=False)

    __table_args__ = (UniqueConstraint("parent_component_id", "child_component_id", name="uq_parent_child"),)

    def __repr__(self):
        return f"<ComponentComponent(id={self.id}, parent_component_id={self.parent_component_id}, child_component_id={self.child_component_id})>"

class Component(Base):
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(200), nullable=False)

    part = relationship('Part', back_populates='component', uselist=False)

    # children: Components that this component is parent of
    children = relationship(
        "Component",
        secondary="component_component",
        primaryjoin=id == ComponentComponent.parent_component_id,
        secondaryjoin=id == ComponentComponent.child_component_id,
        backref=backref("parents", lazy="joined"),
        lazy="joined",
    )

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

    component_id = Column(ForeignKey('components.id'))
    component = relationship('Component', back_populates='part')

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

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    # General information
    name = Column(String, nullable=False) # e.g. Steel plate 12 mm
    standard_number = Column(String) # Standardized number (e.g., 1.4301)
    group = Column(String) # Material group (Steel, Aluminum, Polymer, etc.)
    delivery_condition = Column(String) # Heat treated, annealed, quenched, etc.
    density = Column(Float) # g/cm³

    # Mechanical properties
    elastic_modulus = Column(Float) # Young’s modulus (GPa)
    shear_modulus = Column(Float) # Shear modulus (GPa)
    poisson_ratio = Column(Float) # Dimensionless
    tensile_strength = Column(Float) # Rm, MPa
    yield_strength = Column(Float) # Re or Rp0.2, MPa
    elongation = Column(Float) # Elongation at break, %
    hardness = Column(Float) # hardness value, scale also has to specified
    hardness_scale = Column(String) # e.g., HB, HV, HRC
    toughness = Column(Float) # Charpy impact energy, J
    fatigue_strength = Column(Float) # Endurance limit, MPa

    # Physical properties
    thermal_conductivity = Column(Float) # W/mK
    specific_heat_capacity = Column(Float) # J/kgK
    thermal_expansion = Column(Float) # 1/K
    electrical_conductivity = Column(Float) # S/m
    magnetic_behavior = Column(String) # Ferromagnetic, paramagnetic, diamagnetic

    # Chemical properties
    oxidation_resistance_air = Column(String) # good, limited, poor

    # Technological properties
    weldability = Column(String) # good, limited, poor
    castability = Column(String) # good, limited, poor
    formability = Column(String) # good, limited, poor
    machinability = Column(String) # good, limited, poor
    hardenability = Column(String) # good, limited, poor

    # Operational properties
    temperature_min = Column(String) # Usable min temperature
    temperature_max = Column(String) # Usable max temperature
    wear_resistance = Column(String) # good, limited, poor
    radiation_resistance = Column(String) # good, limited, poor

    # Economic aspects
    price = Column(Float) # Price per kg
    availability = Column(String) # available/ not available
    lead_time = Column(Integer) # lead time for delivery in days


'''
Relationship tables
'''

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



    
