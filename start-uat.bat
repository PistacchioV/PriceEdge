@echo off
REM ============================================================================
REM  PriceEdge - UAT  (Windows)
REM
REM  Werkzeug com auto-reload, porta 5051, so em localhost.
REM  Abre  http://127.0.0.1:5051/  no navegador sozinho.
REM
REM  Uso:  duplo clique.
REM        start-uat.bat noinstall   -> pula a instalacao (util offline)
REM
REM  Nao instala Python. Se o desta estacao estiver num lugar que o script nao
REM  procura, aponte:   set PRICEEDGE_PYTHON=C:\caminho\para\python.exe
REM ============================================================================

setlocal
set "PORTA=5051"
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
REM  O teste e EXECUTAR o candidato, nao verificar se o arquivo existe. O
REM  motivo tem nome: o "App Execution Alias" da Microsoft Store instala um
REM  python.exe de zero byte em %LOCALAPPDATA%\Microsoft\WindowsApps, que entra
REM  no PATH e responde ao `where python`. Ele nao e Python -- ao ser chamado
REM  imprime "Python was not found; run without arguments to install from the
REM  Microsoft Store" e sai. Um launcher que aceita o primeiro python.exe que o
REM  `where` devolve pega esse, e depois falha no pip e no waitress com a mesma
REM  mensagem, sem nunca dizer que o problema e o Python escolhido.
REM
REM  Ordem: variavel de ambiente, venv ao lado, arvore ds\tools da estacao,
REM  instalacoes comuns, o launcher py, e so entao o PATH.
REM ---------------------------------------------------------------------------
set "PY="

call :TESTAR_PYTHON "%PRICEEDGE_PYTHON%"
call :TESTAR_PYTHON "%BASE%.venv\Scripts\python.exe"
call :TESTAR_PYTHON "%BASE%Scripts\python.exe"

REM  layout da estacao: %USERPROFILE%\ds\tools\python3.12\<versao>\python.exe,
REM  com um "latest" ao lado das versoes numeradas
for /d %%d in ("%USERPROFILE%\ds\tools\python3*") do (
    call :TESTAR_PYTHON "%%~fd\latest\python.exe"
    for /d %%v in ("%%~fd\*") do call :TESTAR_PYTHON "%%~fv\python.exe"
)
for /d %%d in ("%USERPROFILE%\ds\tools\*") do call :TESTAR_PYTHON "%%~fd\python.exe"

REM  instalacoes comuns do Windows
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :TESTAR_PYTHON "%%~fd\python.exe"
for /d %%d in ("%ProgramFiles%\Python3*")                 do call :TESTAR_PYTHON "%%~fd\python.exe"
for /d %%d in ("C:\Python3*")                             do call :TESTAR_PYTHON "%%~fd\python.exe"

REM  o launcher py resolve a versao sozinho; o alias da loja tambem se chama py,
REM  por isso ele passa pelo mesmo teste de execucao
call :TESTAR_PYTHON "py"
call :TESTAR_PYTHON "python"
call :TESTAR_PYTHON "python3"

if not defined PY (
    echo.
    echo [ERRO] Nenhum Python que responda foi encontrado.
    echo.
    echo        Procurei, nesta ordem:
    echo          %%PRICEEDGE_PYTHON%%  ^(nao definida^)
    echo          %BASE%.venv\Scripts\python.exe
    echo          %USERPROFILE%\ds\tools\python3*\latest\python.exe
    echo          %USERPROFILE%\ds\tools\python3*\3.12.x\python.exe
    echo          %LOCALAPPDATA%\Programs\Python\Python3*\python.exe
    echo          py / python / python3 no PATH
    echo.
    echo        Se o Python estiver em outro lugar, aponte para ele e rode de novo:
    echo          set PRICEEDGE_PYTHON=C:\caminho\para\python.exe
    echo.
    echo        Um python.exe que existe mas nao responde e, quase sempre, o
    echo        atalho da Microsoft Store em WindowsApps -- ele e ignorado aqui
    echo        de proposito.
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
set "PRECIFICADOR_HOST=127.0.0.1"
set "PRECIFICADOR_DEBUG=1"

REM abre o navegador numa janela propria, que espera o servidor responder
start "PriceEdge UAT - navegador" /min "%~f0" --abrir

echo.
echo [UAT] PriceEdge em %URL%  ^(Werkzeug, auto-reload^)
echo       Feche esta janela ou Ctrl+C para parar.
echo.
"%PY%" "%BASE%run.py"

echo.
echo [INFO] O servidor parou.
popd
pause
exit /b


REM ===========================================================================
:TESTAR_PYTHON
REM  Aceita %~1 como Python so se ele executar e disser a propria versao.
REM  Primeiro candidato que passar vence; os seguintes saem na primeira linha.
REM ===========================================================================
if defined PY exit /b 0
if "%~1"=="" exit /b 0
REM  o atalho da Microsoft Store responde ao `where` e nao e Python
echo %~1 | findstr /I /C:"\WindowsApps\" >nul && exit /b 0
set "MARCA="
REM  max(m,9)==m e nao m>=9: para o cmd, o ">" dentro de um `for /f` e
REM  redirecionamento de saida, mesmo entre aspas. Escrito com ">=", o teste
REM  falharia calado e TODO candidato seria recusado -- inclusive o Python certo.
for /f "usebackq delims=" %%r in (`"%~1" -c "import sys;v=sys.version_info;print('PY3OK' if v[0]==3 and max(v[1],9)==v[1] else 'VELHO')" 2^>nul`) do set "MARCA=%%r"
if /I not "%MARCA%"=="PY3OK" exit /b 0
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
