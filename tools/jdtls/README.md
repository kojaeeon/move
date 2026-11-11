# JDT LS 1.63.0 for OpenIDEA 0.1.40 (Windows, JDK 21)

Official distribution: https://download.eclipse.org/jdtls/milestones/1.63.0/jdt-language-server-1.63.0-202610191322.tar.gz

## Build the portable files on GitHub
1. In this repository open **Actions → Package JDT LS portable → Run workflow**.
2. Wait for the workflow to finish. It commits `jdtls.part000`, etc., and `SHA256SUMS` into this directory.
3. Download all parts, `SHA256SUMS`, and `install.py` to the same folder on the company PC. GitHub source-file downloads are sufficient.

## Windows setup
```bat
py -3.14 install.py
set "JAVA_HOME=C:\\path\\to\\jdk-21"
set "PATH=%CD%\\runtime\\bin;%JAVA_HOME%\\bin;%PATH%"
where jdtls
java -version
```

Launch OpenIDEA **from the same command prompt** so it inherits PATH/JAVA_HOME. Open the Maven project root containing `pom.xml` and then a Java source file. JDT LS starts on demand.

OpenIDEA source references:
- https://github.com/l0ng-ai/openidea/blob/37c2a60/languages/java.toml
- https://github.com/l0ng-ai/openidea/blob/37c2a60/crates/ide-sdk/src/jdtls.rs

## Check process
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'java|openidea' } | Select-Object ProcessId,Name,CommandLine | Format-List
```

Look for `org.eclipse.equinox.launcher` or `org.eclipse.jdt.ls.core`. Test Java completion and Go to Definition.

## Notes
- This repository does **not** include Oracle JDK; reuse an existing compatible JDK 21+.
- The workflow needs repository Actions enabled and **Workflow permissions: Read and write** (or an equivalent permitted token).
- Python 3.14 is used only to reassemble/extract the release; OpenIDEA can start JDT LS directly with Java.
- Downloading the official release via GitHub Actions requires outbound access from the runner.
