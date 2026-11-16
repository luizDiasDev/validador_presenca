$insightface = python -c "import insightface, os; print(os.path.dirname(insightface.__file__))"

pyinstaller `
    --noconfirm `
    --windowed `
    --name ADSUM-Sala `
    --collect-all insightface `
    --collect-all onnxruntime `
    --add-data "$insightface\data\objects;insightface\data\objects" `
    --collect-submodules biometrics `
    --collect-submodules room_app `
    room_app\__main__.py

if (-not (Test-Path "dist\ADSUM-Sala\_internal\insightface\data\objects\meanshape_68.pkl")) {
    throw "meanshape_68.pkl ficou fora do executável."
}
