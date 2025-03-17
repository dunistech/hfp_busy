from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, Enum, ForeignKey, DECIMAL, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

# Database connection
DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'hfp_db')}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class UserRegistrationRequest(Base):
    __tablename__ = 'user_registration_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(Text, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    processed = Column(Boolean, default=False)
    name = Column(String(250))
    phone = Column(String(250))

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    profile_image = Column(Text)
    suspended = Column(Boolean, default=False)
    activation_token = Column(Text)
    is_activated = Column(Boolean, default=False)
    registration_request_id = Column(Integer, ForeignKey('user_registration_requests.id'))
    name = Column(String(250))
    phone = Column(String(250))

    registration_request = relationship("UserRegistrationRequest", back_populates="users")

class BusinessRegistrationRequest(Base):
    __tablename__ = 'business_registration_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_name = Column(String(100), nullable=False)
    shop_no = Column(String(100), nullable=False)
    phone_number = Column(String(20))
    description = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    category = Column(String(50), nullable=False)
    block_num = Column(String(50))
    email = Column(String(100))

class Business(Base):
    __tablename__ = 'businesses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey('users.id'))
    business_name = Column(String(100), nullable=False)
    shop_no = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    is_subscribed = Column(Boolean, default=False)
    media_type = Column(Enum('image', 'video'))
    media_url = Column(Text)
    category = Column(String(50), nullable=False)
    block_num = Column(String(50))
    email = Column(String(100))

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(255), unique=True, nullable=False)

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_name = Column(String(50), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    duration = Column(Integer, nullable=False)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    subscription_date = Column(TIMESTAMP, nullable=False)
    status = Column(Enum('pending', 'confirmed'))
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'))

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    payment_date = Column(TIMESTAMP, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    payment_status = Column(Enum('pending', 'completed'))
    payment_method = Column(String(50))

class ClaimRequest(Base):
    __tablename__ = 'claim_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    phone_number = Column(String(255))
    email = Column(String(255))
    category = Column(String(255))
    description = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False)
    reviewed = Column(Boolean, default=False)

# Create tables in the database
Base.metadata.create_all(engine)
