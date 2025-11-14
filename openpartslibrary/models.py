from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Enum, ForeignKey, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, relationship, backref
from flask_login import UserMixin
from datetime import datetime

class Base(DeclarativeBase):
  pass

'''
Relationship tables
'''
class ComponentComponent(Base):
    __tablename__ = 'component_component'

    id = Column(Integer, primary_key=True)

    parent_component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    child_component_id = Column(Integer, ForeignKey("components.id"), nullable=False)

    __table_args__ = (UniqueConstraint("parent_component_id", "child_component_id", name="uq_parent_child"),)

    def __repr__(self):
        return f"<ComponentComponent(id={self.id}, parent_component_id={self.parent_component_id}, child_component_id={self.child_component_id})>"

class ComponentSupplier(Base):
    __tablename__ = 'component_supplier'

    id = Column(Integer, primary_key=True)

class ComponentFile(Base):
    __tablename__ = 'component_file'

    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    date_linked = Column(DateTime, default=datetime.utcnow)

    __table__args__ = (UniqueConstraint('component_id', 'file_id', name='uq_component_file'),)

'''
Tables
'''
class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.username}, {self.email}>'

class Component(Base):
    __tablename__ = 'components'

    id = Column(Integer, unique=True, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    number = Column(String(50), nullable=False)

    description = Column(String(1000))
    revision = Column(String(10))
    lifecycle_state = Column(String(50))
    owner = Column(String(100))
    material = Column(String(200))
    unit_price = Column(Numeric(10, 2))
    currency = Column(String(3))
    
    # CAD related
    cad_file_id = Column(Integer, ForeignKey('files.id'))
    cad_file = relationship('File', back_populates='cad_component', uselist=False, foreign_keys=[cad_file_id])

    # Supplier
    supplier_id = Column(ForeignKey('suppliers.id'))
    supplier = relationship('Supplier', back_populates='components')
    manufacturer_number = Column(String(100))

    # Many-to-many relationship with Files
    files = relationship('File', secondary='component_file', back_populates='components')
    
    # Enables multi-level hierarchies - components that this component is parent of
    children = relationship(
        "Component",
        secondary = "component_component",
        primaryjoin = id == ComponentComponent.parent_component_id,
        secondaryjoin = id == ComponentComponent.child_component_id,
        backref = backref("parents", lazy="joined"),
        lazy = "joined",
    )

    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Component(id={self.id}, number={self.number}, name={self.name})>"

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

    components = relationship(Component)
    
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

    # Many-to-many relationship with components
    components = relationship('Component', secondary='component_file', back_populates='files')

    # One-to-one relationship with Component for CAD reference
    cad_component = relationship('Component', back_populates='cad_file', uselist=False, foreign_keys='Component.cad_file_id')

# Future feature, not part of MVP
class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(64))               # e.g., 'Metal', 'Polymer', 'Composite'
    
    # --- Basic mechanical properties ---
    density = Column(Float)                     # kg/m³
    youngs_modulus = Column(Float)              # Pa
    poisson_ratio = Column(Float)
    shear_modulus = Column(Float)               # Pa
    bulk_modulus = Column(Float)                # Pa

    # --- Plasticity properties ---
    yield_strength = Column(Float)              # Pa
    ultimate_strength = Column(Float)           # Pa
    hardening_modulus = Column(Float)           # Pa (for isotropic hardening)
    
    # --- Thermal properties ---
    thermal_conductivity = Column(Float)        # W/m·K
    specific_heat = Column(Float)               # J/kg·K
    thermal_expansion = Column(Float)           # 1/K (coefficient of linear expansion)
    
    # --- Damage or failure properties ---
    fracture_toughness = Column(Float)          # MPa·m^0.5
    fatigue_strength = Column(Float)            # Pa
    
    # --- Metadata ---
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Material {self.name}>"

# Future feature, not part of MVP
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






    
