import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc
from typing import List

from . import models, database

app = FastAPI(title="Rezi Roadmap Web App")

# Create database tables if they don't exist (useful for testing without seed first)
models.Base.metadata.create_all(bind=database.engine)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/books")
def get_books(db: Session = Depends(database.get_db)):
    books = db.query(models.Book).all()
    return [{"id": b.id, "name": b.name} for b in books]

@app.get("/api/books/{book_id}/chapters")
def get_chapters(book_id: int, db: Session = Depends(database.get_db)):
    chapters = db.query(models.Chapter).filter(models.Chapter.book_id == book_id).order_by(asc(models.Chapter.number)).all()
    if not chapters:
        raise HTTPException(status_code=404, detail="Chapters not found")
    
    result = []
    for c in chapters:
        sub_chapters = db.query(models.SubChapter).filter(models.SubChapter.chapter_id == c.id).order_by(models.SubChapter.id).all()
        result.append({
            "id": c.id,
            "number": c.number,
            "name": c.name,
            "number_of_pages": c.number_of_pages,
            "sub_chapters": [{
                "id": s.id,
                "number_in_chapter": s.number_in_chapter,
                "name": s.name,
                "page_start": s.page_start,
                "page_end": s.page_end,
                "size": s.size
            } for s in sub_chapters]
        })
    return result
