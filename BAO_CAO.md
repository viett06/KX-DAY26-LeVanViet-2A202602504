# Báo cáo Lab Day 26 — MCP và Function Calling

| | |
|---|---|
| Họ tên | Lê Văn Việt |
| MSSV | 2A202602504 |
| Repo | https://github.com/viett06/KX-DAY26-LeVanViet-2A202602504 |
| Ngày chạy | 14/10/2026 |
| Nguồn lab | [VinUni-AI20k/Day26-MCP-Tools-Integration](https://github.com/VinUni-AI20k/Day26-MCP-Tools-Integration) |

Log gốc của từng bước nằm trong [`reports/evidence/`](reports/evidence/). File `.env` chứa API key và không được commit.

## 1. Mục tiêu

Chạy đủ bốn bước của lab để thấy Function Calling và MCP ở hai tầng khác nhau, rồi nối chúng lại trong một agent thật:

1. Function Calling thuần với Gemini SDK. Schema và hàm `get_weather` nằm trong app. Dữ liệu là mock.
2. MCP cơ bản qua stdio. Server tự công bố tool, client chỉ `list_tools` và `call_tool`.
3. Ba việc của MCP khi đưa lên production: xác thực Bearer token, tool registry, versioning.
4. Agent Google ADK gọi MCP server thời tiết thật (WeatherAPI) qua Streamable HTTP.

## 2. Môi trường

- Bước 01–03: Python 3.11, `pip install -r requirements.txt`.
- Bước 04: `uv sync` riêng trong `04-lab/mcp-server` và `04-lab/mcp-client`.
- `WEATHERAPI_KEY` trong `04-lab/mcp-server/.env`.
- `GEMINI_API_KEY` và `GOOGLE_API_KEY` trong `.env` của bước 01 và bước 04. Cùng một key Gemini.
- MCP server lab 04: `http://localhost:8085/mcp`.
- Auth server bước 03: `http://localhost:8000/mcp`.

`gemini-2.5-flash` trong README trả 404 với API key hiện tại. Google báo model này không còn cho user mới và trỏ sang dòng Gemini 3. `gemini-3.8-flash` đúng tên thay thế nhưng lúc chạy đang quá tải. Bài dùng `gemini-3.5-flash-lite`, model này vẫn có function calling. Đổi model bằng biến `GEMINI_MODEL`.

## 3. Bước 01 — Function Calling

Lệnh: `cd 01-function-calling && python weather_function_calling.py`

Câu hỏi: "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"

```
[model yêu cầu] get_weather({'city': 'Ha Noi'})
[app thực thi]  -> {"city": "Ha Noi", "nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
[model yêu cầu] get_weather({'city': 'Da Nang'})
[app thực thi]  -> {"city": "Da Nang", "nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
```

Model không tự chạy hàm. Nó trả về hai `function_call`. App chạy `get_weather` rồi gửi kết quả lại. Model tổng hợp câu trả lời tiếng Việt: cả hai thành phố 28°C và có lời khuyên thoa kem chống nắng.

Dữ liệu là mock trong app. Từ điển mock dùng "Hà Nội" và "Đà Nẵng" có dấu, còn model gửi "Ha Noi" và "Da Nang", nên hàm rơi vào nhánh mặc định. Việc này cho thấy app thực thi đúng tham số model sinh ra.

Log: [`reports/evidence/01-function-calling.txt`](reports/evidence/01-function-calling.txt)

## 4. Bước 02 — MCP cơ bản

Lệnh: `cd 02-mcp-basics && python weather_client.py`

Client tự spawn `weather_server.py` qua stdio. Không cần API key.

```
Tools server cung cấp:
  - get_weather: Lấy thời tiết hiện tại của một thành phố.

call_tool get_weather(city='Hanoi'):
  -> Hanoi: 29°C, trời mưa
call_tool get_weather(city='Danang'):
  -> Danang: 30°C, nhiều mây
call_tool get_weather(city='Haiphong'):
  -> Haiphong: 33°C, mưa rào
```

Schema sinh từ `@mcp.tool()` và type hint. Client không chứa hàm thời tiết.

Log: [`reports/evidence/02-mcp-basics.txt`](reports/evidence/02-mcp-basics.txt)

## 5. Bước 03 — Production

### 5.1 Auth

Terminal 1: `python auth_server.py` tại `http://localhost:8000/mcp`.

Terminal 2: `python auth_client.py` gửi `Authorization: Bearer dev-token-abc123`.

```
Tools (có auth):
  - get_weather: Lấy thời tiết hiện tại của một thành phố.

Kết quả: Hanoi: 29°C, trời mưa
```

Hàm tool không kiểm tra token. SDK kiểm tra ở tầng transport.

Log: [`reports/evidence/03-auth-client.txt`](reports/evidence/03-auth-client.txt)

### 5.2 Tool registry

Lệnh: `python registry_client.py`

Registry liệt kê `get_weather` v1, `get_weather_v2` v2, `send_email`, `query_db`. Tìm theo tag `weather` ra 2 tool. Best match là `get_weather_v2` v2.0.0 vì version cao hơn và không deprecated. Agent tự nối server `weather-v2` và nhận JSON `Hanoi, 29°C, trời mưa`.

Log: [`reports/evidence/03-registry.txt`](reports/evidence/03-registry.txt)

### 5.3 Versioning

Lệnh: `python versioned_client.py`

```
Server: weather-v2 v2.0.0
Deprecated tools: ['get_weather']
Migration: Chuyển từ get_weather sang get_weather_v2.
           Tham số 'city' giữ nguyên, thêm include_forecast và units.

[v1] get_weather('Hanoi'):
  Hanoi: 29°C, trời mưa

[v2] get_weather_v2('Hanoi', forecast=True):
  api_version 2.0, temp 29, units celsius, forecast 2 ngày
```

Tool v1 vẫn chạy. Tool v2 thêm forecast và đơn vị đo. Metadata nằm ở resource `server://info`.

Log: [`reports/evidence/03-versioned.txt`](reports/evidence/03-versioned.txt)

## 6. Bước 04 — Agent ADK và MCP server thật

### Server

`cd 04-lab/mcp-server && uv run python weather.py`

Server Streamable HTTP tại `http://localhost:8085/mcp`. Ba tool: `get_current_weather`, `get_forecast`, `health_check`. Gọi trực tiếp qua MCP client:

- `health_check` — server đang chạy.
- `get_current_weather("Hanoi")` — 28.8°C, Cloudy, độ ẩm 67%, gió 17.6 km/h. Số liệu từ WeatherAPI, cập nhật 14/10/2026 20:15.
- `get_forecast("Danang", 2)` — 14/10: 21.4–27.3°C, sương mù, 86% mưa. 15/10: 20.4–28.9°C, sương mù, 60% mưa.

### Agent

`verify_setup.py`: cả 5 mục đều đạt (key, dependency, cấu trúc agent, MCP server HTTP 406 vì GET không phải session MCP, import `weather_agent`). Model lúc import: `gemini-3.5-flash-lite`.

Log: [`reports/evidence/04-verify-setup.txt`](reports/evidence/04-verify-setup.txt)

Agent chạy bằng ADK `InMemoryRunner`, cùng `root_agent` mà `adk web` nạp. ADK tự `list_tools`, đưa schema cho Gemini, gọi MCP server, rồi đưa kết quả lại cho model.

Câu 1: "Thời tiết hiện tại ở Hà Nội thế nào? Cho tôi dự báo 2 ngày ở Đà Nẵng."

```
[tool call] get_current_weather({'city': 'Hanoi'})
[tool call] get_forecast({'days': 2, 'city': 'Danang'})
```

Câu trả lời dùng đúng số liệu server: Hà Nội 28.8°C, cảm giác 31.7°C, nhiều mây, độ ẩm 67%. Đà Nẵng 14/10 mưa 86%, 15/10 mưa 60%. Lời khuyên mang ô vì sương mù và mưa.

Câu 2: "Dịch vụ thời tiết có đang chạy không?"

```
[tool call] health_check({})
```

Agent trả lời dịch vụ đang hoạt động, khớp chuỗi của tool.

Log đầy đủ, gồm HTTP 200 tới `localhost:8085/mcp` và `generateContent`: [`reports/evidence/04-adk-agent.txt`](reports/evidence/04-adk-agent.txt)

Giao diện web của lab là `uv run adk web` rồi mở http://localhost:8000, chọn `weather_agent`. Phần chấm hành vi agent ở trên chạy cùng `root_agent` và cùng MCP server, không qua trình duyệt.

## 7. Kết luận

Function Calling là khả năng của model: model chọn tool và sinh tham số, app hoặc server mới chạy tool. MCP là giao thức để một server tự mô tả tool và nhiều client dùng chung. Bước 04 là chỗ hai tầng gặp nhau. Gemini quyết định gọi tool. ADK là MCP client. FastMCP server gọi WeatherAPI.

Ba điểm production đã chạy được trên máy: Bearer token trên HTTP, registry chọn tool theo tag và version, song song v1 deprecated với v2.

## 8. Checklist nộp

- [x] Bước 01 chạy được và có vòng lặp function calling
- [x] Bước 02 `list_tools` + `call_tool` qua stdio
- [x] Bước 03 auth, registry, versioning
- [x] Bước 04 MCP server thật và agent gọi đủ 3 tool
- [x] `verify_setup.py` đạt
- [x] Báo cáo và log trong repo
- [x] `.env` nằm trong `.gitignore`
- [ ] Commit, push lên GitHub, dán link repo trên VLearn

Cloud Run không nằm trong đường chạy bắt buộc của README. Lab 04 đã hoàn thành trên server local.
