@echo off
REM ============================================================================
REM  PriceEdge - PRODUCAO  (Windows)
REM
REM  Waitress (servidor WSGI), porta 5050, em todas as interfaces.
REM  Abre  http://127.0.0.1:5050/  no navegador sozinho; a rede chega pelo
REM  http://<IP-da-maquina>:5050/
REM
REM  Uso:  duplo clique.
REM        start-prod.bat noinstall   -> pula a instalacao (util offline)
REM
REM  Nao instala Python. Se o desta estacao estiver num lugar que o script nao
REM  procura, aponte:   set PRICEEDGE_PYTHON=C:\caminho\para\python.exe
REM ============================================================================

setlocal
set "PORTA=5050"
set "URL=http://127.0.0.1:%PORTA%/"

REM ---------------------------------------------------------------------------
REM  Reentrada: chamado com --abrir, este mesmo .bat nao sobe nada. So espera a
REM  porta responder e abre o navegador. E o jeito de abrir a pagina sozinho sem
REM  aspas aninhadas dentro de `cmd /c`, que e onde essa linha costuma quebrar.
REM ---------------------------------------------------------------------------
if /I "%~1"=="--abrir" goto :ABRIR_NAVEGADOR

REM ---------------------------------------------------------------------------
REM  UNC-safe: `cd /d` nao aceita caminho de rede -- o cmd responde "UNC paths
REM  are not supported", cai em C:\Windows e segue. Dali o run.py nao e achado e
REM  o servidor nem sobe. O pushd mapeia o share numa letra temporaria.
REM ---------------------------------------------------------------------------
pushd "%~dp0" 2>nul
if errorlevel 1 (
    echo [ERRO] Nao consegui acessar a pasta: %~dp0
    pause
    exit /b 1
)

set "BASE=%~dp0"

REM ---------------------------------------------------------------------------
REM  Localiza o Python. NAO instala nada.
REM
REM  Duas regras, e as duas vieram de erro em maquina de verdade:
REM
REM  1) O teste e EXECUTAR o candidato, nao verificar se o arquivo existe. O
REM     "App Execution Alias" da Microsoft Store instala um python.exe de zero
REM     byte em %LOCALAPPDATA%\Microsoft\WindowsApps, que entra no PATH e
REM     responde ao `where python`. Ele nao e Python -- ao ser chamado imprime
REM     "Python was not found; run without arguments to install from the
REM     Microsoft Store" e sai. Quem aceita o primeiro python.exe do `where`
REM     pega esse, e depois falha no pip e no waitress com a mesma mensagem.
REM
REM  2) A varredura usa `dir /b /s`, e NAO `for /d` com curinga. Num `for /d`,
REM     um padrao entre aspas -- for /d %%d in ("C:\...\python3*") -- e tratado
REM     como texto literal: o curinga nao expande, %%~fd vira o proprio
REM     "...\python3*" e o caminho testado nunca existe. Tirar as aspas faria o
REM     curinga funcionar mas quebraria em "C:\Program Files". `dir /b /s`
REM     resolve os dois casos e ainda acha o python.exe em qualquer
REM     profundidade, sem precisar adivinhar o nome da pasta de versao.
REM ---------------------------------------------------------------------------
set "PY="

call :TESTAR_PYTHON "%PRICEEDGE_PYTHON%"
call :TESTAR_PYTHON "%BASE%.venv\Scripts\python.exe"
call :TESTAR_PYTHON "%BASE%Scripts\python.exe"

REM  arvore de ferramentas da estacao -- e onde mora o Python aqui, sem venv
call :VARRER "%USERPROFILE%\ds\tools"
call :VARRER "%USERPROFILE%\ds"
call :VARRER "%LOCALAPPDATA%\Programs\Python"
call :VARRER "%LOCALAPPDATA%\Programs\Python\Python312"
call :VARRER "%ProgramFiles%\Python312"
call :VARRER "%ProgramFiles(x86)%\Python312"
call :VARRER "C:\Python312"
call :VARRER "C:\Python311"

REM  o launcher py resolve a versao sozinho; passa pelo mesmo teste de execucao
call :TESTAR_PYTHON "py"
call :TESTAR_PYTHON "python"
call :TESTAR_PYTHON "python3"

if not defined PY (
    echo.
    echo [ERRO] Nenhum Python que responda foi encontrado.
    echo.
    echo        Procurei python.exe, recursivamente, em:
    echo          %USERPROFILE%\ds\tools
    echo          %LOCALAPPDATA%\Programs\Python
    echo          %ProgramFiles%\Python312   e   C:\Python312
    echo        e tentei py, python e python3 no PATH.
    echo.
    echo        Aponte o caminho e rode de novo:
    echo          set PRICEEDGE_PYTHON=C:\Users\seu.usuario\ds\tools\python3.12\latest\python.exe
    echo.
    echo        Para ver cada candidato testado e por que foi recusado:
    echo          set PRICEEDGE_DEBUG=1
    echo.
    echo        Um python.exe que existe mas nao responde e, quase sempre, o
    echo        atalho da Microsoft Store em WindowsApps -- ignorado aqui de
    echo        proposito.
    echo.
    popd
    pause
    exit /b 1
)
echo [INFO] Python: %PY%
for /f "usebackq delims=" %%v in (`"%PY%" -c "import sys;print(sys.version.split()[0])" 2^>nul`) do echo [INFO] Versao: %%v

REM ---------------------------------------------------------------------------
REM  Dependencias, best-effort: se o pypi estiver bloqueado, avisa e segue com o
REM  que ja esta instalado -- numa estacao corporativa esse e o caso comum.
REM ---------------------------------------------------------------------------
if /I "%~1"=="noinstall" (
    echo [INFO] Instalacao de dependencias pulada ^(noinstall^).
) else (
    echo.
    echo [INFO] Instalando dependencias ^(requirements.txt^)...
    "%PY%" -m pip install -r "%BASE%requirements.txt" --timeout 10 --retries 1 --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo [AVISO] Nao consegui instalar/atualizar as dependencias ^(rede/pypi^).
        echo         Seguindo com o que ja esta instalado.
        echo.
    )
)

REM ---------------------------------------------------------------------------
REM  Bytecode em disco local. Rodando de um share, o Python grava um .pyc por
REM  modulo pela rede na primeira subida depois de um pull -- centenas de
REM  gravacoes atomicas, minutos parado sem imprimir nada, com cara de travado.
REM  Nao use PYTHONDONTWRITEBYTECODE: evita a escrita mas obriga a recompilar
REM  tudo a cada subida. %LOCALAPPDATA% e nao %TEMP%, que a Limpeza de Disco
REM  apaga.
REM ---------------------------------------------------------------------------
if not defined PYTHONPYCACHEPREFIX set "PYTHONPYCACHEPREFIX=%LOCALAPPDATA%\PriceEdge\pycache"

set "PRECIFICADOR_PORTA=%PORTA%"
set "PRECIFICADOR_HOST=0.0.0.0"
set "PRECIFICADOR_DEBUG=0"

REM abre o navegador numa janela propria, que espera o servidor responder
start "PriceEdge - navegador" /min "%~f0" --abrir

echo.
echo [PRODUCAO] PriceEdge em http://0.0.0.0:%PORTA%  ^(waitress^)
echo            Feche esta janela ou Ctrl+C para parar.
echo.
REM ---------------------------------------------------------------------------
REM  Waitress e nao gunicorn: gunicorn nao roda no Windows.
REM
REM  Escale com THREADS, nunca com processos. O cache de curvas da B3 vive na
REM  memoria do processo -- com dois processos, cada um baixa e guarda a sua
REM  copia, e duas telas abertas lado a lado podem mostrar curvas de momentos
REM  diferentes. Alem disso a maior parte do tempo de um request aqui e espera
REM  de rede (B3, BCB, NY Fed, Banco da Finlandia): a thread fica parada
REM  segurando a vaga, e com as quatro vagas padrao do waitress quatro esperas
REM  dessas param o servidor inteiro, inclusive para quem so pediu um CSS.
REM ---------------------------------------------------------------------------
"%PY%" -m waitress --host=0.0.0.0 --port=%PORTA% --threads=16 run:app
if errorlevel 1 (
    echo.
    echo [ERRO] waitress nao subiu. Instale com:  "%PY%" -m pip install waitress
)

echo.
echo [INFO] O servidor parou.
popd
pause
exit /b


REM ===========================================================================
:VARRER
REM  Testa todo python.exe sob %~1, em qualquer profundidade.
REM  `dir /b /s` imprime caminho completo e lida com espaco no caminho, que e
REM  onde o `for /d` com curinga entre aspas falhava calado.
REM ===========================================================================
if defined PY exit /b 0
if "%~1"=="" exit /b 0
if not exist "%~1" (
    if defined PRICEEDGE_DEBUG echo [DEBUG] pasta inexistente: %~1
    exit /b 0
)
for /f "usebackq delims=" %%p in (`dir /b /s "%~1\python.exe" 2^>nul`) do call :TESTAR_PYTHON "%%p"
exit /b 0

REM ===========================================================================
:TESTAR_PYTHON
REM  Aceita %~1 como Python so se ele executar e disser a propria versao.
REM  Primeiro candidato que passar vence; os seguintes saem na primeira linha.
REM ===========================================================================
if defined PY exit /b 0
if "%~1"=="" exit /b 0
REM  o atalho da Microsoft Store responde ao `where` e nao e Python
echo %~1 | findstr /I /C:"\WindowsApps\" >nul && (
    if defined PRICEEDGE_DEBUG echo [DEBUG] recusado ^(atalho da Microsoft Store^): %~1
    exit /b 0
)
set "MARCA="
REM  max(m,9)==m e nao m>=9: para o cmd, o ">" dentro de um `for /f` e
REM  redirecionamento de saida, mesmo entre aspas. Escrito com ">=", o teste
REM  falharia calado e TODO candidato seria recusado -- inclusive o Python certo.
for /f "usebackq delims=" %%r in (`"%~1" -c "import sys;v=sys.version_info;print('PY3OK' if v[0]==3 and max(v[1],9)==v[1] else 'VELHO')" 2^>nul`) do set "MARCA=%%r"
if /I not "%MARCA%"=="PY3OK" (
    if defined PRICEEDGE_DEBUG echo [DEBUG] recusado ^(nao respondeu^): %~1
    exit /b 0
)
if defined PRICEEDGE_DEBUG echo [DEBUG] aceito: %~1
set "PY=%~1"
exit /b 0


REM ===========================================================================
:ABRIR_NAVEGADOR
REM  Espera o servidor atender antes de abrir a pagina. Sem isto o navegador
REM  chega antes e mostra "nao foi possivel acessar" -- o servidor sobe em
REM  segundos numa maquina rapida e em bem mais de um share lento, entao um
REM  `timeout` fixo erra dos dois lados. Aqui o teste e a porta responder.
REM
REM  netstat e nao PowerShell: Test-NetConnection so aceita o operador ternario
REM  no PowerShell 7, e a estacao vem com o 5.1 -- ali a linha falharia calada e
REM  o navegador abriria cedo demais, toda vez.
REM ===========================================================================
set "TENTATIVAS=0"
:ESPERAR
set /a TENTATIVAS+=1
if %TENTATIVAS% GTR 60 goto :ABRIR_ASSIM_MESMO
netstat -an | findstr /C:":%PORTA% " | findstr /I /C:"LISTENING" >nul 2>&1
if not errorlevel 1 goto :ABRIR_ASSIM_MESMO
REM  ping como pausa de ~1s: sempre existe, ao contrario do timeout, que falha
REM  com "input redirection is not supported" quando nao ha console interativo
ping -n 2 127.0.0.1 >nul 2>&1
goto :ESPERAR

:ABRIR_ASSIM_MESMO
start "" "%URL%"
exit /b
