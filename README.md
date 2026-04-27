# Netflix Clone Backend FastAPI

Backend FastAPI cho NetflixClone Service App.

## Architecture

- Service App iOS -> Netflix Clone FastAPI BE (`http://localhost:5000`)
- Netflix Clone FastAPI BE -> SuperApp BE (`http://localhost:8000`) cho OIDC token exchange

## API Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/oidc/token`
- `GET /health`

## Prerequisites

- Python 3.10+ (khuyến nghị Python 3.11)
- `pip`

Kiểm tra nhanh:

```bash
python3 --version
pip --version
```

## Run (Recommended: venv)

```bash
cd /Users/ndhunq/Documents/GitHub/netflix-clone-backend-fastapi

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python run.py

# Nếu cổng 5000 đang bị chiếm (thường gặp trên macOS), đổi cổng như sau:
PORT=5001 python run.py
```

Server chạy tại:

- API: `http://localhost:5000`
- Swagger: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

## Run (Without venv)

```bash
cd /Users/ndhunq/Documents/GitHub/netflix-clone-backend-fastapi
pip3 install -r requirements.txt
python3 run.py
```

## Verify Backend

### 1) Health check

```bash
curl http://localhost:5000/health
```

Expected:

```json
{"status":"ok","service":"netflix-clone-backend-fastapi"}
```

### 2) Run quick API test script

```bash
cd /Users/ndhunq/Documents/GitHub/netflix-clone-backend-fastapi
python test_api.py
```

## Default user

Tự động seed khi startup nếu chưa có:

- `phone_number`: `0901234567`
- `password`: `Password1`

## Notes for iOS integration

- Service App cần gọi đúng endpoint token exchange:
	- `POST http://localhost:5000/auth/oidc/token`
- Endpoint này sẽ forward request sang SuperApp BE:
	- `POST http://localhost:8000/oidc/token`

## Common Issues

### Port 5000 already in use

Trên macOS, tiến trình `ControlCenter` (AirPlay Receiver) có thể chiếm cổng 5000.

```bash
lsof -i :5000
kill -9 <PID>
```

Hoặc chạy backend ở cổng khác:

```bash
PORT=5001 python run.py
```

### Command not found: uvicorn / fastapi modules

Bạn chưa cài dependencies đúng environment.

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### SuperApp BE chưa chạy

OIDC exchange sẽ fail nếu `http://localhost:8000` không available.

## Project Entry Points

- Start server: `run.py`
- App object: `app/main.py`
- Auth routes: `app/api/auth.py`
- Test script: `test_api.py`
