@echo off
REM Delete all local branches except main, master, and development

for /f "skip=1" %%b in ('git branch --format="%%(refname:short)"') do (
    if /I not "%%b"=="main" (
        if /I not "%%b"=="master" (
            if /I not "%%b"=="development" (
                echo Deleting branch %%b
                git branch -D %%b
            )
        )
    )
)

echo Done.
pause
