from fastapi import FastAPI, Depends, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from google.cloud import storage
import uuid
from datetime import datetime
from pydantic import BaseModel
import os
import uvicorn

from database import get_db, History

app = FastAPI()

# add cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Cloud Storage setup
storage_client = storage.Client()
bucket_name = os.getenv("BUCKET_NAME")  # Get bucket name from environment variable
bucket = storage_client.bucket(bucket_name)

class HistoryResponse(BaseModel):
    prompt: str
    image_url: str
    created_at: datetime

@app.get("/history", response_model=List[HistoryResponse])
def get_history(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    history = db.query(History) \
        .order_by(History.created_at.desc()) \
        .offset(skip) \
        .limit(limit) \
        .all()
    return history

class SaveImageRequest(BaseModel):
    prompt: str
    image: UploadFile

@app.post("/save")
async def save_image(
    request: SaveImageRequest,
    db: Session = Depends(get_db)
):
    # Upload image to Google Cloud Storage
    try:
        # Generate unique filename
        file_extension = request.image.filename.split(".")[-1]
        blob_name = f"generations/{uuid.uuid4()}.{file_extension}"
        blob = bucket.blob(blob_name)
        
        # Upload the file
        contents = await request.image.read()
        blob.upload_from_string(contents, content_type=request.image.content_type)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Get the public URL
        image_url = blob.public_url
        
        # Save to database
        db_history = History(
            prompt=request.prompt,
            image_url=image_url
        )
        db.add(db_history)
        db.commit()
        db.refresh(db_history)
        
        return {"prompt": request.prompt, "image_url": image_url}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def hello_world():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
