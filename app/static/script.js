document.addEventListener('DOMContentLoaded', () => {
    const booksContainer = document.getElementById('books-container');
    const chaptersContainer = document.getElementById('chapters-container');
    const booksView = document.getElementById('books-view');
    const chaptersView = document.getElementById('chapters-view');
    const backBtn = document.getElementById('back-btn');
    const pageTitle = document.getElementById('page-title');

    // Fetch and render books on load
    fetchBooks();

    backBtn.addEventListener('click', () => {
        showBooksView();
    });

    async function fetchBooks() {
        try {
            const response = await fetch('/api/books');
            const books = await response.json();
            renderBooks(books);
        } catch (error) {
            console.error('Error fetching books:', error);
            booksContainer.innerHTML = '<p>Error loading books. Please try again later.</p>';
        }
    }

    function renderBooks(books) {
        booksContainer.innerHTML = '';
        books.forEach(book => {
            const card = document.createElement('div');
            card.className = 'book-card';
            card.innerHTML = `
                <i class="fa-solid fa-book-open book-icon"></i>
                <div class="book-title">${book.name}</div>
            `;
            card.addEventListener('click', () => fetchAndRenderChapters(book));
            booksContainer.appendChild(card);
        });
    }

    async function fetchAndRenderChapters(book) {
        try {
            const response = await fetch(`/api/books/${book.id}/chapters`);
            const chapters = await response.json();
            
            // Update UI
            pageTitle.textContent = book.name;
            backBtn.classList.remove('hidden');
            
            renderChapters(chapters);
            
            // Switch views
            booksView.classList.remove('active');
            booksView.classList.add('hidden');
            chaptersView.classList.remove('hidden');
            chaptersView.classList.add('active');
        } catch (error) {
            console.error('Error fetching chapters:', error);
        }
    }

    function renderChapters(chapters) {
        chaptersContainer.innerHTML = '';
        chapters.forEach(chapter => {
            const item = document.createElement('div');
            item.className = 'chapter-item';
            
            // Header
            const header = document.createElement('div');
            header.className = 'chapter-header';
            header.innerHTML = `
                <div class="chapter-number">CAP ${chapter.number}</div>
                <div class="chapter-title">${chapter.name}</div>
                <i class="fa-solid fa-chevron-down chapter-icon"></i>
            `;
            
            // Subchapters container
            const subContainer = document.createElement('div');
            subContainer.className = 'subchapters-container';
            
            const subList = document.createElement('div');
            subList.className = 'subchapters-list';
            
            if (chapter.sub_chapters && chapter.sub_chapters.length > 0) {
                chapter.sub_chapters.forEach(sub => {
                    const subItem = document.createElement('div');
                    subItem.className = 'subchapter-item';
                    
                    let pagesText = '';
                    if (sub.page_start > 0) {
                        pagesText = sub.page_end > sub.page_start 
                            ? `p.${sub.page_start}-${sub.page_end}` 
                            : `p.${sub.page_start}`;
                    }

                    subItem.innerHTML = `
                        <div class="subchapter-name">
                            <i class="fa-solid fa-file-lines" style="color: var(--muted-text); font-size: 0.8rem;"></i>
                            ${sub.number_in_chapter ? sub.number_in_chapter + '. ' : ''}${sub.name}
                        </div>
                        ${pagesText ? `<div class="subchapter-pages">${pagesText}</div>` : ''}
                    `;
                    subList.appendChild(subItem);
                });
            } else {
                subList.innerHTML = '<div style="color: var(--muted-text); font-style: italic;">No subchapters</div>';
            }
            
            subContainer.appendChild(subList);
            item.appendChild(header);
            item.appendChild(subContainer);
            
            // Toggle accordion
            header.addEventListener('click', () => {
                // Close others
                document.querySelectorAll('.chapter-item.expanded').forEach(expandedItem => {
                    if (expandedItem !== item) {
                        expandedItem.classList.remove('expanded');
                    }
                });
                
                // Toggle current
                item.classList.toggle('expanded');
            });
            
            chaptersContainer.appendChild(item);
        });
    }

    function showBooksView() {
        pageTitle.textContent = "Trixy's progress";
        backBtn.classList.add('hidden');
        
        chaptersView.classList.remove('active');
        chaptersView.classList.add('hidden');
        booksView.classList.remove('hidden');
        booksView.classList.add('active');
    }
});
