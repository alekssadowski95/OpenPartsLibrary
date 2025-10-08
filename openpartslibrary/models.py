from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Enum, ForeignKey, UniqueConstraint, Boolean, Text
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
    is_archived = Column(Boolean, default=False)

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

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(64))  # e.g., 'Metal', 'Polymer', 'Composite'
    
    # --- Basic mechanical properties ---
    density = Column(Float)                    # kg/m³
    youngs_modulus = Column(Float)             # Pa
    poisson_ratio = Column(Float)
    shear_modulus = Column(Float)              # Pa
    bulk_modulus = Column(Float)               # Pa

    # --- Plasticity properties ---
    yield_strength = Column(Float)             # Pa
    ultimate_strength = Column(Float)          # Pa
    hardening_modulus = Column(Float)          # Pa (for isotropic hardening)
    
    # --- Thermal properties ---
    thermal_conductivity = Column(Float)       # W/m·K
    specific_heat = Column(Float)              # J/kg·K
    thermal_expansion = Column(Float)          # 1/K (coefficient of linear expansion)
    
    # --- Damage or failure properties ---
    fracture_toughness = Column(Float)         # MPa·m^0.5
    fatigue_strength = Column(Float)           # Pa
    
    # --- Metadata ---
    supplier = Column(String(256))               
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Material {self.name}>"
    

class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)            
    title = Column(String(200), nullable=False)                           
    description = Column(Text, nullable=False)                            
    requirement_type = Column(Enum("mandatory", "minimum", "desirable", name="requirement_type"), nullable=False)
    owner = Column(String(100))                                
    acceptance_criteria = Column(Text)      
    source = Column(String(200))      
    created_at = Column(DateTime, default=datetime.utcnow)                                                    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Requirement {self.uuid}: {self.title}>"

"""
sample_requirements = [
    {
        "uuid": uuid.uuid4().hex,
        "title": "Maximum Jaw Opening",
        "description": "The vise shall accommodate workpieces up to 200 mm wide.",
        "requirement_type": "mandatory",
        "owner": "Alice Smith",
        "acceptance_criteria": "Measured jaw opening ≥ 200 mm with gauge.",
        "source": "Customer specification"
    },
    {
        "uuid": uuid.uuid4().hex,
        "title": "Clamping Force",
        "description": "The vise shall provide a clamping force of at least 1500 N to securely hold workpieces.",
        "requirement_type": "mandatory",
        "owner": "Bob Johnson",
        "acceptance_criteria": "Verified using load cell measurement during clamping test.",
        "source": "Engineering requirement"
    },
    {
        "uuid": uuid.uuid4().hex,
        "title": "Jaw Parallelism",
        "description": "The vise jaws shall maintain parallelism within 0.05 mm along the entire opening range.",
        "requirement_type": "minimum",
        "owner": "Carol Lee",
        "acceptance_criteria": "Measured with precision dial gauge along jaw faces.",
        "source": "Quality control standard"
    },
    {
        "uuid": uuid.uuid4().hex,
        "title": "Surface Finish of Jaws",
        "description": "The vise jaws should have a smooth, polished finish to prevent workpiece damage.",
        "requirement_type": "desirable",
        "owner": "David Kim",
        "acceptance_criteria": "Visual inspection; minor surface scratches acceptable.",
        "source": "Design recommendation"
    },
    {
        "uuid": uuid.uuid4().hex,
        "title": "Rotatable Base",
        "description": "The vise base should be rotatable 360° for flexible workpiece orientation.",
        "requirement_type": "desirable",
        "owner": "Eve Martinez",
        "acceptance_criteria": "Base rotation smooth, full 360° rotation without obstruction.",
        "source": "Optional feature"
    },
    {
        "uuid": uuid.uuid4().hex,
        "title": "Material Hardness",
        "description": "The vise body shall be made of steel with a hardness of at least 200 HB.",
        "requirement_type": "mandatory",
        "owner": "Frank Li",
        "acceptance_criteria": "Hardness verified with Rockwell or Brinell test.",
        "source": "Mechanical design standard"
    }
]
"""

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



    
