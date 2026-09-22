from .database import Base, engine, SessionLocal
from .models import User
from .auth import hash_password

Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    if not db.query(User).filter_by(email="admin@hlb.local").first():
        db.add(User(email="admin@hlb.local",full_name="System Administrator",password_hash=hash_password("Me123!"),role="Admin")); db.commit()
        print("Admin created. Change the password immediately.")
    else: print("Admin already exists.")
finally: db.close()
