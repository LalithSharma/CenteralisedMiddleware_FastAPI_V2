from datetime import datetime
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from DLL.schemas import ShowRoleResponse, ShowUsersResponse, UserCreation, UserUpdate
from auth.dependencies import  get_current_user, get_db, get_user
from auth.utils import get_password_hash
from logger import log_error, log_info
from .schemas import UserSchema
from .models import Role, User as UserModel, UserChannel, UserRole
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

DATABASE_URL = os.getenv("DB_CONNECTIVITY")

engine = create_engine(DATABASE_URL)

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


@router.get("/showusers", response_model=ShowUsersResponse)
def get_user_role_channels(db: Session = Depends(get_db)):
    try:
        userList = []
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM user_role_channel_view"))
            for row in result:
                row_dict = dict(row._mapping)

                # Convert datetime fields to ISO strings
                if isinstance(row_dict["created_at"], datetime):
                    row_dict["created_at"] = row_dict["created_at"].isoformat()

                userList.append(row_dict)

        print("Converted rows as dict:", userList) 
        return {
            "message": "User retrieved successfully",
            "result": True,
            "data": userList
        }
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/roles")
def get_roles(db: Session = Depends(get_db)):
    try:
        roles = db.query(Role).all()
        result = [ShowRoleResponse.model_validate(ch).model_dump() for ch in roles]
        return {
            "message": "Roles retrieved successfully",
            "result": True,
            "data": result
        }
    except Exception as e:
        # Log the error if you want
        print("Error fetching roles:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/createuser", status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreation, db: Session = Depends(get_db)):
    try:
        # Step 1: Check if user already exists
        db_user = get_user(db, email=user_data.email)
        if db_user:
            raise HTTPException(status_code=400, detail="User already exists")

        # Step 2: Insert user
        hashed_password = get_password_hash(user_data.password)
        new_user = UserModel(
            email=user_data.email,
            hashed_password=hashed_password,
            status=user_data.status,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Step 3: Add channels
        for channel_id in user_data.channels:
            db.add(UserChannel(user_id=new_user.id, channel_id=channel_id))
        db.commit()

        # Step 4: Add roles
        for role_id in user_data.roles:
            db.add(UserRole(user_id=new_user.id, role_id=role_id))
        db.commit()

        return {"message": "User created successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/updateuser/{user_id}")
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    try:
        # Step 1: Find the existing user
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Step 2: Update fields if provided
        if user_data.email:
            user.email = user_data.email
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        if user_data.status is not None:
            user.status = user_data.status

        db.commit()
        db.refresh(user)
        
        # Step 3: Update roles (clear old and add new)
        if user_data.roles is not None:
            db.query(UserRole).filter(UserRole.user_id == user_id).delete()
            for role_id in user_data.roles:
                db.add(UserRole(user_id=user_id, role_id=role_id))
            db.commit()
        
        # Step 4: Update channels (clear old and add new)
        if user_data.channels is not None:
            db.query(UserChannel).filter(UserChannel.user_id == user_id).delete()
            for channel_id in user_data.channels:
                db.add(UserChannel(user_id=user_id, channel_id=channel_id))
            db.commit()

        return {"message": "User updated successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/remove/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        # Step 1: Find the user
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Step 2: Delete related roles and channels
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        db.query(UserChannel).filter(UserChannel.user_id == user_id).delete()

        # Step 3: Delete user
        db.delete(user)
        db.commit()

        return {"message": f"User with ID {user_id} deleted successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))