@echo off
if "%1"=="" (
	echo Usage: write.bat BOOK_NAME CHAPTER_COUNT GIST
	echo Example: write.bat MyNovel 20 "A story about hope."
	echo.
	echo Steps:
	echo   1. Initialize:   write.bat MyNovel 20 "A story about hope."
	echo   2. Layout:       write.bat MyNovel 20 "A story about hope."
	echo   3. Draft:        write.bat MyNovel
	echo   4. Publish:      write.bat MyNovel
	echo   5. Read:         write.bat MyNovel
	exit /b 1
)
python book.py init --book-name %1 --chapter-count %2 --verbose --debug
python book.py layout --book-name %1 --gist %3 --verbose --debug
python book.py draft --book-name %1 --verbose --debug
python book.py publish --book-name %1 --verbose --debug
python book.py read --book-name %1 --verbose --debug
