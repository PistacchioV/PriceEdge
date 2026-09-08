@echo off
REM ============================================================================
REM  PriceEdge - PRODUCAO  (Windows)
REM
REM  Waitress (servidor WSGI), porta 5050, em todas as interfaces.
REM  Abre  http://127.0.0.1:5050/  no navegador sozinho; a rede chega pelo
REM  http://IP-da-maquina:5050/
REM
REM  Uso:  duplo clique.
REM        start-prod.bat noinstall   ... pula a instalacao (util offline)
REM
REM  Nao instala Python. Se o desta estacao estiver num lugar que o script nao
REM  procura, aponte:   set PRICEEDGE_PYTHON=C:\caminho\para\python.exe
REM ============================================================================

setlocal
set "PORTA=5050"
set "URL=http://127.0.0.1:%PORTA%/"
REM  porta do agente de proxy local da estacao (localproxy-cfg)
set "PROXY_LOCAL_PORTA=9443"

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
REM  Caminho conhecido e resolvido com `if exist`: e instantaneo e nao depende
REM  de nada. Um python.exe dentro de ds\tools ou de Programs\Python e o Python
REM  de verdade -- nao ha o que validar ali.
REM
REM  Ja o que vem do PATH passa por teste de execucao, porque e exatamente la
REM  que mora o "App Execution Alias" da Microsoft Store: um python.exe de zero
REM  byte em %LOCALAPPDATA%\Microsoft\WindowsApps que responde ao `where` e, ao
REM  ser chamado, so imprime "Python was not found; run without arguments to
REM  install from the Microsoft Store". Foi ele que o launcher pegou na
REM  primeira tentativa, e por isso o pip e o waitress falharam com essa mesma
REM  mensagem, sem nunca dizer que o problema era o Python escolhido.
REM ---------------------------------------------------------------------------
set "PY="

REM  QuickEdit: um clique dentro do console poe a janela em modo de selecao e
REM  CONGELA o processo ate um Esc. O titulo passa a comecar com "Select". Como
REM  a tela fica parada sem explicacao nenhuma, o aviso vem antes de tudo.
echo [DICA] Se o titulo da janela comecar com "Select", o console esta em modo
echo        de selecao e o processo fica congelado. Aperte Esc para destravar.
echo.

if defined PRICEEDGE_PYTHON if exist "%PRICEEDGE_PYTHON%" set "PY=%PRICEEDGE_PYTHON%"
if not defined PY if exist "%BASE%.venv\Scripts\python.exe" set "PY=%BASE%.venv\Scripts\python.exe"
if not defined PY if exist "%BASE%Scripts\python.exe"       set "PY=%BASE%Scripts\python.exe"

REM  layout desta estacao: ds\tools\python3.NN\latest\python.exe
for %%n in (3.13 3.12 3.11 3.10) do (
    if not defined PY if exist "%USERPROFILE%\ds\tools\python%%n\latest\python.exe" set "PY=%USERPROFILE%\ds\tools\python%%n\latest\python.exe"
    if not defined PY if exist "%USERPROFILE%\ds\tools\python%%n\python.exe"        set "PY=%USERPROFILE%\ds\tools\python%%n\python.exe"
)

REM  instalacoes comuns do Windows
for %%n in (313 312 311 310) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%n\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%n\python.exe"
    if not defined PY if exist "%ProgramFiles%\Python%%n\python.exe"                 set "PY=%ProgramFiles%\Python%%n\python.exe"
    if not defined PY if exist "C:\Python%%n\python.exe"                             set "PY=C:\Python%%n\python.exe"
)

if defined PY if defined PRICEEDGE_DEBUG echo [DEBUG] achado por caminho: %PY%

REM  ---- so agora o PATH, e so ele passa por teste de execucao --------------
call :TESTAR_PYTHON "py"
call :TESTAR_PYTHON "python"
call :TESTAR_PYTHON "python3"

REM  ---- ultimo recurso: varrer, e so pasta pequena e local ----------------
REM  NUNCA varra %USERPROFILE% inteiro nem %USERPROFILE%\ds: essas arvores
REM  costumam ter junction para share de rede, e `dir /s` entra nelas -- a
REM  busca some por minutos numa tela preta, sem imprimir nada, com cara de
REM  travada. Foi o que aconteceu aqui.
if not defined PY echo [INFO] Nao achei nos caminhos usuais; varrendo ds\tools...
call :VARRER "%USERPROFILE%\ds\tools"
call :VARRER "%LOCALAPPDATA%\Programs\Python"

if not defined PY (
    echo.
    echo [ERRO] Nenhum Python foi encontrado.
    echo.
    echo        Procurei em:
    echo          %USERPROFILE%\ds\tools\python3.1x\latest\python.exe
    echo          %LOCALAPPDATA%\Programs\Python\Python31x\python.exe
    echo          %ProgramFiles%\Python31x   e   C:\Python31x
    echo          py, python e python3 no PATH
    echo        e varri %USERPROFILE%\ds\tools e a pasta Programs\Python.
    echo.
    echo        Aponte o caminho e rode de novo:
    echo          set PRICEEDGE_PYTHON=C:\Users\seu.usuario\ds\tools\python3.12\latest\python.exe
    echo.
    echo        Para ver cada candidato testado:  set PRICEEDGE_DEBUG=1
    echo.
    popd
    pause
    exit /b 1
)
echo [INFO] Python: %PY%
for /f "usebackq delims=" %%v in (`"%PY%" -c "import sys;print(sys.version.split()[0])" 2^>nul`) do echo [INFO] Versao: %%v

REM ---------------------------------------------------------------------------
REM  Proxy. Numa rede corporativa a saida direta nao existe: sem proxy a chamada
REM  morre em WinError 10060 -- timeout de TCP, nao erro de HTTP.
REM
REM  O detalhe que engana: a estacao pode ter HTTP_PROXY definido e ESTE
REM  processo nao enxergar. Variavel exportada pelo perfil de um terminal vive
REM  naquele terminal; o cmd que o duplo clique abre nao a recebe. Por isso o
REM  valor visto e impresso aqui -- em branco quer dizer saida direta.
REM
REM  PRICEEDGE_PROXY define o proxy so para esta sessao. Para fixar de vez:
REM      setx HTTP_PROXY  http://127.0.0.1:9443
REM      setx HTTPS_PROXY http://127.0.0.1:9443
REM ---------------------------------------------------------------------------
if defined PRICEEDGE_PROXY (
    set "HTTP_PROXY=%PRICEEDGE_PROXY%"
    set "HTTPS_PROXY=%PRICEEDGE_PROXY%"
    set "PRECIFICADOR_PROXY=%PRICEEDGE_PROXY%"
)
REM  Sem proxy na sessao, procura o agente local: o localproxy-cfg da estacao
REM  sobe um proxy em 127.0.0.1:9443 e exporta as variaveis, mas elas ficam no
REM  terminal que rodou o setup -- nao chegam ao cmd do duplo clique. Se a porta
REM  estiver escutando, o agente esta de pe e da para usa-lo.
REM
REM  Detectar e usar, sim; instalar, nao. Se o agente nao estiver instalado,
REM  quem resolve e o bootstrap da estacao (`ds tool install localproxy-cfg`),
REM  nao um script de subida de aplicacao.
if not defined HTTPS_PROXY if not defined HTTP_PROXY (
    netstat -an | findstr /C:":%PROXY_LOCAL_PORTA% " | findstr /I /C:"LISTENING" >nul 2>&1
    if not errorlevel 1 (
        set "HTTP_PROXY=http://127.0.0.1:%PROXY_LOCAL_PORTA%"
        set "HTTPS_PROXY=http://127.0.0.1:%PROXY_LOCAL_PORTA%"
        echo [INFO] Agente de proxy local detectado na porta %PROXY_LOCAL_PORTA%.
    )
)

if defined HTTPS_PROXY (
    echo [INFO] Proxy: %HTTPS_PROXY%
) else (
    if defined HTTP_PROXY (
        echo [INFO] Proxy: %HTTP_PROXY%
    ) else (
        echo [AVISO] Nenhum proxy nesta sessao -- a saida vai direto.
        echo         Se as fontes derem timeout ^(WinError 10060^):
        echo           1. confirme que o agente local esta de pe
        echo              ^(ds tool list ^| findstr localproxy-cfg^)
        echo           2. ou aponte o proxy a mao:
        echo              set PRICEEDGE_PROXY=http://127.0.0.1:9443
        echo         Depois confira em Metodologia, botao "Testar as fontes".
    )
)

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
REM ---------------------------------------------------------------------------
REM  SSO Kerberos. No ambiente do JP toda chamada externa sai autenticada, e o
REM  Negotiate depende do requests-negotiate-sspi (ja nos requirements, com
REM  marcador de plataforma). Ligado, a camada de rede LEVANTA erro se o pacote
REM  faltar, em vez de sair sem autenticacao e receber um 401 do ADFS -- que
REM  chega a tela como uma URL de duas mil letras sem mencionar pacote nenhum.
REM
REM  Para desligar numa maquina fora do banco:  set PRICEEDGE_SEM_SSO=1
REM ---------------------------------------------------------------------------
if not defined PRICEEDGE_SEM_SSO set "PRECIFICADOR_SSO=1"
if defined PRICEEDGE_SEM_SSO echo [INFO] SSO Kerberos desligado por PRICEEDGE_SEM_SSO.
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
echo [INFO]   varrendo %~1 ...
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
REM  max(m,9)==m e nao uma comparacao de maior-ou-igual: para o cmd, o sinal
REM  de maior e redirecionamento de saida dentro de um `for /f`, mesmo entre
REM  aspas -- escrito da forma obvia, o teste falharia calado e recusaria TODO
REM  candidato, inclusive o Python certo. E REM nao protege: o cmd processa
REM  redirecionamento tambem em linha de comentario.
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
