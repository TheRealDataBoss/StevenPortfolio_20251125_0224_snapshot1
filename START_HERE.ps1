Set-Location "C:\Users\Steven\Portfolio"
.\.venv\Scripts\Activate.ps1

Write-Host "=== Interpreter ==="
python --version
python -c "import sys; print(sys.executable)"

Write-Host "=== Django Checks ==="
python manage.py check

Write-Host "=== Django Tests ==="
python manage.py test

Write-Host "=== Smoke Test ==="
python .\smoke_test.py

Write-Host "=== Start Server ==="
python manage.py runserver 127.0.0.1:8000
