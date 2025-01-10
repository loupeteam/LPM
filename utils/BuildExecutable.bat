cd ..
pyinstaller --onefile --clean --add-data src\version.json:. --version-file="version.txt" --icon=files\favicon.ico src\LPM.py 
