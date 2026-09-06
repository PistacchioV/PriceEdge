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
REM ============================================================================

setlocal
set "PORTA=5050"
set "URL=http://127.0.0.1:%PORTA%/"

REM ---------------------------------------------------------------------------
REM  Reentrada: quando este mesmo .bat e chamado com --abrir, ele nao sobe nada.
REM  So espera o servidor responder e abre o navegador. E o jeito de abrir a
REM  pagina sozinho sem aspas aninhadas dentro de `cmd /c`, que e onde essa
REM  linha costuma quebrar.
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
REM  Localiza o Python. Nao instala nada: se nao houver Python nesta maquina,
REM  o script para e diz o que falta, em vez de tentar resolver sozinho.
REM ---------------------------------------------------------------------------
set "PY="
if exist "%BASE%.venv\Scripts\python.exe"     set "PY=%BASE%.venv\Scripts\python.exe"
if not defined PY if exist "%BASE%Scripts\python.exe" set "PY=%BASE%Scripts\python.exe"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    where py >nul 2>&1 && set "PY=py"
)

if not defined PY (
    echo.
    echo [ERRO] Python nao encontrado nesta maquina.
    echo        Instale o Python 3.10 ou mais novo, ou crie o virtualenv:
    echo            python -m venv .venv
    echo.
    popd
    pause
    exit /b 1
)
echo [INFO] Python: %PY%

REM ---------------------------------------------------------------------------
REM  Dependencias, best-effort: se o pypi estiver bloqueado, avisa e segue com
REM  o que ja esta instalado -- numa maquina corporativa esse e o caso comum.
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
:ABRIR_NAVEGADOR
REM  Espera o servidor atender antes de abrir a pagina. Sem isto o navegador
REM  chega antes e mostra "nao foi possivel acessar" -- o servidor sobe em
REM  segundos numa maquina rapida e em bem mais de um share lento, entao um
REM  `timeout` fixo erra dos dois lados. Aqui o teste e a porta responder.
REM ===========================================================================
REM  netstat e nao PowerShell: Test-NetConnection so aceita o operador ternario
REM  no PowerShell 7, e a maquina corporativa vem com o 5.1 -- ali a linha
REM  falha calada e o navegador abre cedo demais, toda vez. netstat existe em
REM  qualquer Windows e nao depende de politica de execucao.
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
