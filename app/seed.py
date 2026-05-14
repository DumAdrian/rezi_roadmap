import json
import os
from .database import engine, SessionLocal, Base
from .models import Book, Author, Chapter, SubChapter

# Book titles as provided by user
BOOK_DATA = {
    "book_1": {"name": "Medicina Clinica", "author": "Adam Feather"},
    "book_2": {"name": "Chirurgie si specialitati chirurgicale", "author": "Peter F"},
    "book_3": {"name": "Sinopsis de medicina", "author": "Latha Ganti"}
}

def seed():
    # Create tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Load JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'parse_result.json')
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    books = data.get("books", {})
    
    for book_key, book_info in books.items():
        book_metadata = BOOK_DATA.get(book_key, {"name": f"Unknown Book {book_key}", "author": "Unknown Author"})
        
        # Create author
        author = db.query(Author).filter(Author.full_name == book_metadata["author"]).first()
        if not author:
            author = Author(full_name=book_metadata["author"], role="author")
            db.add(author)
            db.commit()
            db.refresh(author)
        
        # Create book
        book = Book(
            id=book_info["book_id"],
            name=book_metadata["name"],
            edition="1st",
            publisher="Unknown",
            year=2026
        )
        book.authors.append(author)
        db.add(book)
        db.commit()
        db.refresh(book)

        # Create chapters
        for ch in book_info.get("chapters", []):
            chapter = Chapter(
                number=ch.get("cap_number"),
                name=ch.get("title", ""),
                number_of_pages=ch.get("book_page_count", 0),
                book_id=book.id
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)

            # Create subchapters
            for sub in ch.get("subchapters", []):
                span = sub.get("book_page_span")
                page_start = span[0] if span else 0
                page_end = span[1] if span and len(span) > 1 else page_start
                size = sub.get("book_page_count", 0)

                sub_chapter = SubChapter(
                    number_in_chapter=str(sub.get("number", "")),
                    name=sub.get("title", ""),
                    page_start=page_start,
                    page_end=page_end,
                    size=size,
                    chapter_id=chapter.id
                )
                db.add(sub_chapter)
            db.commit()
    
    print("Database seeding completed.")
    db.close()

if __name__ == "__main__":
    seed()
