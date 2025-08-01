from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Define base class for models
Base = declarative_base()

# Define a User model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

    def __repr__(self):
        return f"<User(name='{self.name}', email='{self.email}')>"

def print_all_users(session):
    users = session.query(User).all()
    print('\n')
    print('Users:')
    print('------')
    for user in users:
        print(user)
    print('------')



# Create an SQLite database in memory (use 'sqlite:///example.db' for file-based)
engine = create_engine('sqlite:///example.db')

# Create all tables
Base.metadata.create_all(engine)

# Create a session
SessionFactory = sessionmaker(bind=engine)
session = SessionFactory()

# Add a new user
user_1 = User(name='Alice', email='alice@example.com')
session.add(user_1)
session.commit()
    
# Add a new user
user_2 = User(name='Max', email='max@example.com')
session.add(user_2)
session.commit()

# Print all users
print_all_users(session)