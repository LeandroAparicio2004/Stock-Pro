@echo off
echo Instalando dependencias...
pip install -r requirements.txt pyinstaller

echo Generando .exe...
pyinstaller --onefile --windowed --name "StockPro" ^
  --add-data "db;db" ^
  --add-data "modules;modules" ^
  app.py

echo.
echo Listo! El .exe esta en la carpeta dist/
pause