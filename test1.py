# Debug book.py layout command directly
import sys
import book

if __name__ == "__main__":
    sys.argv = [
        "book.py",
        "layout",
        "--book-name", "testbook",
        "--gist", "Test gist for book",
        "--debug"
    ]
    book.main()
