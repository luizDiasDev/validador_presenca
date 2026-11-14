pyinstaller `
    --noconfirm `
    --windowed `
    --name ADSUM-Sala `
    --collect-all insightface `
    --collect-all onnxruntime `
    --collect-submodules biometrics `
    --collect-submodules room_app `
    room_app\__main__.py
