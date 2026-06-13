@echo off
echo Building RaKScribe26 Standalone Executable...
echo.

pyinstaller --onefile --noconsole --name=rakscribe26 --icon=rakscribe.ico ^
  --add-data "C:\Python312\Lib\site-packages\customtkinter;customtkinter/" ^
  --exclude-module torch ^
  --exclude-module torchvision ^
  --exclude-module scipy ^
  --exclude-module pandas ^
  --exclude-module matplotlib ^
  --exclude-module cv2 ^
  --exclude-module paddle ^
  --exclude-module paddlex ^
  --exclude-module paddleocr ^
  --exclude-module sqlalchemy ^
  --exclude-module pg8000 ^
  --exclude-module psycopg ^
  --exclude-module psycopg_binary ^
  --exclude-module mysqlclient ^
  --exclude-module pymysql ^
  --exclude-module pyodbc ^
  --exclude-module redis ^
  --exclude-module pymongo ^
  --exclude-module elasticsearch ^
  --exclude-module neo4j ^
  --exclude-module influxdb ^
  --exclude-module clickhouse_driver ^
  --exclude-module openpyxl ^
  --exclude-module xlsxwriter ^
  --exclude-module xlrd ^
  --exclude-module xlwt ^
  --exclude-module docx ^
  --exclude-module pptx ^
  --exclude-module sympy ^
  --exclude-module mpmath ^
  --exclude-module networkx ^
  --exclude-module PIL.SpiderImagePlugin ^
  --exclude-module PIL.FpxImagePlugin ^
  --exclude-module PIL.MicImagePlugin ^
  --exclude-module PIL.MspImagePlugin ^
  --exclude-module PIL.PalmImagePlugin ^
  --exclude-module PIL.PdfImagePlugin ^
  --exclude-module PIL.PixarImagePlugin ^
  --exclude-module PIL.PcdImagePlugin ^
  --exclude-module PIL.PcxImagePlugin ^
  --exclude-module PIL.SgiImagePlugin ^
  --exclude-module PIL.TgaImagePlugin ^
  --exclude-module PIL.WmfImagePlugin ^
  --exclude-module PIL.XbmImagePlugin ^
  --exclude-module PIL.XpmImagePlugin ^
  --exclude-module PIL.XVThumbImagePlugin ^
  --exclude-module langchain ^
  --exclude-module langchain_community ^
  --exclude-module langchain_core ^
  --exclude-module langchain_openai ^
  --exclude-module langsmith ^
  --exclude-module litellm ^
  --exclude-module llama_cpp ^
  --exclude-module llama_cpp_python ^
  --exclude-module modelscope ^
  --exclude-module skyvern ^
  --exclude-module playright ^
  --exclude-module playwright ^
  --exclude-module onnxruntime ^
  --exclude-module weasyprint ^
  --exclude-module jupyterlab ^
  --exclude-module ipython ^
  --exclude-module jedi ^
  --exclude-module traitlets ^
  --exclude-module parso ^
  --exclude-module pdfminer ^
  --exclude-module pdfplumber ^
  --exclude-module pypdf ^
  --exclude-module pypdfium2 ^
  --exclude-module pytesseract ^
  --exclude-module reportlab ^
  RaKScribe.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] rakscribe26.exe built successfully in the 'dist' folder!
) else (
    echo.
    echo [ERROR] Build failed.
)
pause
