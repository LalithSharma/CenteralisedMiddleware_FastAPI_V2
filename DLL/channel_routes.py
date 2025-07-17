from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.dependencies import get_db
from DLL.schemas import ChannelCreate, ChannelResponse, ChannelUpdate
from users.models import Channel
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

# Create a new channel
@router.post("/createchannel", response_model=ChannelResponse)
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    try:
        print("shows saved channels", channel)  # Fixed typo: should print the instance, not the class

        # Check if the channel already exists
        db_channel = db.query(Channel).filter(Channel.name == channel.name).first()
        if db_channel:
            raise HTTPException(status_code=400, detail="Channel already exists")

        # Create and save the new channel
        new_channel = Channel(**channel.dict())
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)

        return new_channel

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Read all channels
@router.get("/showchannel")
def get_channels(db: Session = Depends(get_db)):
    try:
        channels = db.query(Channel).all()
        result = [ChannelResponse.model_validate(ch).model_dump() for ch in channels]
        return {
            "message": "Channels retrieved successfully",
            "result": True,
            "data": result
        }
    except Exception as e:
        # Log the error if you want
        print("Error fetching channels:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# # Update a channel
@router.put("/update/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, updates: ChannelUpdate, db: Session = Depends(get_db)):
    try:
        # Step 1: Find the existing channel
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        # Step 2: Apply updates
        for key, value in updates.dict(exclude_unset=True).items():
            setattr(channel, key, value)

        db.commit()
        db.refresh(channel)

        return channel

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Delete a channel
@router.delete("/remove/{channel_id}")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    try:
        # Step 1: Find the channel
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        # Step 2: Delete the channel
        db.delete(channel)
        db.commit()

        return {"message": "Channel deleted successfully", "result": True}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))