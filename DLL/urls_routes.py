from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.dependencies import get_db
from DLL.schemas import ApiRoutePathBase, RoutepathResponse
from users.models import APIRoute
from sqlalchemy.exc import SQLAlchemyError


router = APIRouter()

# Create a new Route
@router.post("/createpath", response_model=ApiRoutePathBase)
def create_routePath(pathurls: ApiRoutePathBase, db: Session = Depends(get_db)):
    try:
        print("shows saved urls path", pathurls)

        # Check if route path already exists
        db_APIRoute = db.query(APIRoute).filter(APIRoute.path == pathurls.path).first()
        if db_APIRoute:
            raise HTTPException(status_code=400, detail="Route Path name already exists")
        
        # Create new route path
        new_APIRoute = APIRoute(**pathurls.dict())
        db.add(new_APIRoute)
        db.commit()
        db.refresh(new_APIRoute)

        return new_APIRoute

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Read all api path
@router.get("/showpath")
def get_routePath(db: Session = Depends(get_db)):
    try:
        paths = db.query(APIRoute).all()
        print("display path", paths)
        result = [RoutepathResponse.model_validate(ph).model_dump() for ph in paths]
        print("diplay router urls ", result)
        return {
            "message": "api urls retrieved successfully",
            "result": True,
            "data": result
        }
    except Exception as e:
        # Log the error if you want
        print("Error fetching route path url:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
# # Update a Route
@router.put("/updatepath/{route_id}", response_model=ApiRoutePathBase)
def update_routePath(route_id: int, updates: ApiRoutePathBase, db: Session = Depends(get_db)):
    try:
        routeUpdate = db.query(APIRoute).filter(APIRoute.id == route_id).first()
        if not routeUpdate:
            raise HTTPException(status_code=404, detail="Router url not found")
        
        for key, value in updates.dict(exclude_unset=True).items():
            setattr(routeUpdate, key, value)
        
        db.commit()
        db.refresh(routeUpdate)
        return routeUpdate

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Delete a Route
@router.delete("/removepath/{route_id}")
def delete_routePath(route_id: int, db: Session = Depends(get_db)):
    try:
        route = db.query(APIRoute).filter(APIRoute.id == route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route path url not found")
        
        db.delete(route)
        db.commit()
        return {"message": "Route path url deleted successfully", "result": True}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))