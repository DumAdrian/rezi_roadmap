from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

book_author_association = Table(
    'book_author', Base.metadata,
    Column('book_id', Integer, ForeignKey('book.id'), primary_key=True),
    Column('author_id', Integer, ForeignKey('author.id'), primary_key=True)
)

class Author(Base):
    __tablename__ = 'author'

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    role = Column(String)  # "author" or "romanian version"

    books = relationship("Book", secondary=book_author_association, back_populates="authors")

class Book(Base):
    __tablename__ = 'book'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    edition = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    year = Column(Integer, nullable=True)

    authors = relationship("Author", secondary=book_author_association, back_populates="books")
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")

class Chapter(Base):
    __tablename__ = 'chapter'

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer)
    name = Column(String)
    number_of_pages = Column(Integer)
    book_id = Column(Integer, ForeignKey('book.id'))

    book = relationship("Book", back_populates="chapters")
    sub_chapters = relationship("SubChapter", back_populates="chapter", cascade="all, delete-orphan")

class SubChapter(Base):
    __tablename__ = 'sub_chapter'

    id = Column(Integer, primary_key=True, index=True)
    number_in_chapter = Column(String)
    name = Column(String)
    page_start = Column(Integer)
    page_end = Column(Integer)
    size = Column(Integer)
    chapter_id = Column(Integer, ForeignKey('chapter.id'))

    chapter = relationship("Chapter", back_populates="sub_chapters")
