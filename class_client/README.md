# Executável de sala do ADSUM

Roda no computador da sala: mostra o QR Code da chamada aberta e, quando um aluno lê o QR no
celular, captura o rosto com prova de vida e envia ao servidor **apenas** o vetor facial e as
medidas de prova de vida (nunca a imagem, nunca a identidade do aluno).

## Rodar em desenvolvimento

```powershell
cd class_client
python -m venv .venv-class
.\.venv-class\Scripts\Activate.ps1
pip install -r requirements.txt
python -m room_app
```

No primeiro uso a janela pede:
1. o endereço do servidor (padrão: https://adsum.up.railway.app);
2. o **código de pareamento** de 4 dígitos, que o administrador vê em *Campus e Máquinas → Máquinas*.

A configuração (servidor e token da máquina) fica em `%USERPROFILE%\.adsum\sala.json`.
Para parear de novo, apague esse arquivo.

## Funcionamento na sala

O executável fica em segundo plano, com o ícone dourado "A" ao lado do relógio do Windows. Sem chamada
aberta, não aparece nenhuma janela. Quando a chamada abre, uma janela pequena surge no canto inferior
direito com o QR Code e, depois, com a câmera durante a verificação facial. Quando a chamada fecha, a
janela some sozinha. Um clique no ícone mostra ou esconde a janela; passar o mouse mostra a situação.

Para abrir junto com o Windows, crie um atalho do `ADSUM-Sala.exe` na pasta que abre com
`Win + R` → `shell:startup`. Para fechar o programa, use o Gerenciador de Tarefas.

## Testes

```powershell
pytest
```

Os testes com o modelo real só rodam com `$env:ADSUM_REAL_MODELS = "1"`.

## Gerar o .exe

```powershell
.\build_exe.ps1
```

## Estrutura

- `biometrics/`: câmera, InsightFace, qualidade, captura das amostras, desafio de virar a cabeça e montagem do envio.
- `room_app/`: a janela (PySide6), o cliente da API, a configuração local e a sessão de captura.
- `tools/try_face_engine.py`: ferramenta de desenvolvimento para ver o reconhecimento ao vivo.
