@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem === EDIT THESE PATHS ===
set "WILDFLY_HOME=C:\Work1\SCOBS\wildfly-37.0.0.Final"
set "CDD_PROJECT=C:\Work1\SCOBS\51006-kais-cdd-app"
set "WEB_PROJECT=C:\Work1\SCOBS\50198-kais-web"
set "MAVEN_CMD=mvn.cmd"
rem JAVA_HOME must point to JDK 21; copy required STS JVM options into JAVA_OPTS.
set "SERVER_CONFIG=standalone.xml"
set "BIND_ADDRESS=localhost"
set "DEPLOY_NAME=kais-web.war"
set "MGMT_HOST=localhost"
set "MGMT_PORT=9990"
set "DEPLOY_DIR=%WILDFLY_HOME%\standalone\deployments"
set "WAR_FILE=%WEB_PROJECT%\target\%DEPLOY_NAME%"
set "CLI=%WILDFLY_HOME%\bin\jboss-cli.bat"

if "%~1"=="" goto usage
if /I "%~1"=="start" goto start
if /I "%~1"=="stop" goto stop
if /I "%~1"=="restart" goto restart
if /I "%~1"=="build" goto build
if /I "%~1"=="cdd" goto cdd
if /I "%~1"=="deploy" goto deploy
if /I "%~1"=="publish" goto publish
if /I "%~1"=="status" goto status
if /I "%~1"=="log" goto log
if /I "%~1"=="help" goto usage
echo Unknown command: %~1
exit /b 2

:start
if not exist "%WILDFLY_HOME%\bin\standalone.bat" (echo WildFly not found & exit /b 1)
start "WildFly 37" /D "%WILDFLY_HOME%\bin" cmd /k "call standalone.bat -c %SERVER_CONFIG% -b %BIND_ADDRESS%"
echo WildFly launch requested. Check the new console for startup errors.
exit /b 0

:stop
call "%CLI%" --connect --controller=%MGMT_HOST%:%MGMT_PORT% --command=":shutdown"
exit /b %errorlevel%

:restart
call :stop
if errorlevel 1 exit /b 1
timeout /t 5 /nobreak >nul
call :start
exit /b %errorlevel%

:build
if not exist "%CDD_PROJECT%\pom.xml" (echo CDD pom.xml not found & exit /b 1)
if not exist "%WEB_PROJECT%\pom.xml" (echo WEB pom.xml not found & exit /b 1)
pushd "%CDD_PROJECT%" || exit /b 1
call "%MAVEN_CMD%" clean install -DskipTests
if errorlevel 1 (popd & echo CDD build failed & exit /b 1)
popd
pushd "%WEB_PROJECT%" || exit /b 1
call "%MAVEN_CMD%" clean package -DskipTests
if errorlevel 1 (popd & echo WEB build failed & exit /b 1)
popd
exit /b 0

:cdd
rem Build/install CDD, repackage WEB with updated dependency, then redeploy.
if not exist "%CDD_PROJECT%\pom.xml" (echo CDD pom.xml not found & exit /b 1)
if not exist "%WEB_PROJECT%\pom.xml" (echo WEB pom.xml not found & exit /b 1)
pushd "%CDD_PROJECT%" || exit /b 1
call "%MAVEN_CMD%" install -DskipTests
if errorlevel 1 (popd & echo CDD build failed & exit /b 1)
popd
pushd "%WEB_PROJECT%" || exit /b 1
call "%MAVEN_CMD%" package -DskipTests
if errorlevel 1 (popd & echo WEB packaging failed & exit /b 1)
popd
call :deploy
exit /b %errorlevel%

:deploy
if not exist "%WAR_FILE%" (echo WAR not found: "%WAR_FILE%" & exit /b 1)
if not exist "%DEPLOY_DIR%" (echo Deployments directory not found & exit /b 1)
rem Packaged WAR via management CLI, not an exploded incremental publish.
call "%CLI%" --connect --controller=%MGMT_HOST%:%MGMT_PORT% --command="deploy %WAR_FILE% --name=%DEPLOY_NAME% --runtime-name=%DEPLOY_NAME% --force"
exit /b %errorlevel%

:publish
call :build
if errorlevel 1 exit /b 1
call :deploy
exit /b %errorlevel%

:status
call "%CLI%" --connect --controller=%MGMT_HOST%:%MGMT_PORT% --command=":read-attribute(name=server-state)"
if errorlevel 1 exit /b 1
call "%CLI%" --connect --controller=%MGMT_HOST%:%MGMT_PORT% --command="deployment-info"
exit /b %errorlevel%

:log
if not exist "%WILDFLY_HOME%\standalone\log\server.log" (echo Server log not found & exit /b 1)
powershell -NoProfile -Command "Get-Content -LiteralPath '%WILDFLY_HOME%\standalone\log\server.log' -Tail 100 -Wait"
exit /b %errorlevel%

:usage
echo Usage: server.bat ^<start^|stop^|restart^|build^|cdd^|deploy^|publish^|status^|log^>
echo Edit WILDFLY_HOME, CDD_PROJECT, WEB_PROJECT, JAVA_HOME and optional JAVA_OPTS first.
exit /b 0
