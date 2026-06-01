# Individual Report: Lab 3 - Chatbot vs ReAct Agent

**Student Name:** Lương Quốc Đoàn
**Student ID:** 2A202600564
**Date:** 30/05/2026

---

# I. Technical Contribution (15 Points)

## Mô tả đóng góp kỹ thuật

Trong bài Lab 3, tôi chịu trách nhiệm phát triển và tích hợp hai công cụ chính cho ReAct Agent là Weather Tool và Hotel Search Tool. Mục tiêu là giúp Agent có thể truy xuất thông tin thời tiết và tìm kiếm thông tin khách sạn theo địa điểm mà người dùng yêu cầu.

Weather Tool được kết nối với API thời tiết thông qua API Key được lưu trong file .env. Công cụ này cho phép Agent lấy dữ liệu thời tiết hiện tại và dự báo thời tiết để hỗ trợ người dùng lên kế hoạch du lịch.

Hotel Search Tool được xây dựng để truy vấn thông tin khách sạn, bao gồm tên khách sạn, vị trí, giá phòng và các thông tin liên quan. Công cụ này được tích hợp vào vòng lặp ReAct để Agent có thể tự quyết định khi nào cần tìm kiếm khách sạn và sử dụng kết quả trả về cho bước suy luận tiếp theo.

Ngoài việc phát triển các Tool, tôi cũng tham gia kiểm thử luồng Thought → Action → Observation → Final Answer nhằm đảm bảo Agent có thể phối hợp nhiều công cụ để giải quyết các yêu cầu du lịch nhiều bước thay vì chỉ trả lời bằng kiến thức có sẵn như Chatbot truyền thống.

### Modules Implemented

- `src/agent/react_agent.py`
- `src/tools/search_tool.py`
- `src/tools/calculator_tool.py`
- `src/core/parser.py`
- `src/core/agent_loop.py`

### Code Highlights

#### 1. Xây dựng Agent Loop

```python
while not finished:
    thought = llm.generate(prompt)
    action = parser.extract_action(thought)
    observation = execute_tool(action)
    memory.append(observation)
```

#### 2. Tích hợp Search Tool

```python
def search(query: str):
    return search_engine.search(query)
```

#### 3. Tích hợp Calculator Tool

```python
def calculate(expression: str):
    return eval(expression)
```

### Documentation

Hệ thống được xây dựng theo mô hình ReAct gồm các bước:

1. User gửi câu hỏi.
2. LLM sinh ra Thought.
3. Agent quyết định Action cần thực hiện.
4. Tool được gọi.
5. Tool trả về Observation.
6. Observation được đưa lại cho Agent.
7. Agent tiếp tục suy luận cho tới khi đưa ra Final Answer.

Luồng hoạt động:

```text
User Question
      |
      v
   Thought
      |
      v
    Action
      |
      v
     Tool
      |
      v
 Observation
      |
      v
   Thought ...
      |
      v
 Final Answer
```

---

# II. Debugging Case Study (10 Points)

## Problem Description

Trong quá trình kiểm thử Agent, tôi gặp lỗi Agent bị lặp vô hạn khi gọi Search Tool.

Ví dụ:

```text
Thought: I need more information.
Action: search(None)

Observation: Invalid query.

Thought: I need more information.
Action: search(None)
```

Agent liên tục thực hiện cùng một hành động mà không thể kết thúc.

## Log Source

Trích xuất từ file log:

```text
2026-06-01 10:15:02
Thought: I need more information.
Action: search(None)

2026-06-01 10:15:03
Observation: Invalid query.

2026-06-01 10:15:04
Thought: I need more information.
Action: search(None)
```

## Diagnosis

Nguyên nhân được xác định là:

- Prompt chưa mô tả rõ định dạng Action.
- Model không hiểu rằng tham số tìm kiếm phải là chuỗi hợp lệ.
- Parser không kiểm tra dữ liệu đầu vào trước khi gọi Tool.

Do đó LLM sinh ra:

```text
search(None)
```

thay vì:

```text
search("weather in Hanoi")
```

## Solution

Tôi thực hiện ba biện pháp:

### 1. Bổ sung ví dụ trong System Prompt

```text
Thought: I need weather information.
Action: search("weather in Hanoi")
```

### 2. Thêm validation

```python
if query is None:
    raise ValueError("Query cannot be empty")
```

### 3. Thêm giới hạn số vòng lặp

```python
MAX_STEPS = 10
```

Sau khi áp dụng các thay đổi trên, Agent hoạt động ổn định và không còn rơi vào vòng lặp vô hạn.

---

# III. Personal Insights: Chatbot vs ReAct (10 Points)

## Reasoning

Điểm khác biệt lớn nhất giữa Chatbot và ReAct Agent là khả năng suy luận từng bước.

### Chatbot

Chatbot cố gắng trả lời trực tiếp dựa trên kiến thức sẵn có:

```text
Question:
Find the cheapest hotel and calculate total cost for 3 nights.
```

Chatbot thường chỉ đưa ra câu trả lời mang tính phỏng đoán.

### ReAct Agent

ReAct Agent thực hiện:

```text
Thought:
I need hotel prices.

Action:
search_hotel()

Observation:
Hotel A = $40/night

Thought:
Calculate total cost.

Action:
calculator(40 * 3)

Observation:
120

Final Answer:
Total cost is $120.
```

Nhờ có Thought block, Agent có thể chia nhỏ bài toán và xử lý chính xác hơn.

---

## Reliability

Một số trường hợp Agent hoạt động kém hơn Chatbot:

### 1. Câu hỏi đơn giản

Ví dụ:

```text
What is Python?
```

Chatbot trả lời ngay lập tức.

Trong khi đó Agent phải:

```text
Thought
Action
Observation
Final Answer
```

gây tăng độ trễ không cần thiết.

### 2. Tool hoạt động không ổn định

Nếu Tool lỗi:

```text
API Timeout
Network Error
```

Agent có thể không hoàn thành nhiệm vụ.

Trong khi Chatbot vẫn có thể trả lời dựa trên kiến thức nội bộ.

---

## Observation

Observation đóng vai trò rất quan trọng.

Ví dụ:

```text
Thought:
Need current weather.

Action:
search_weather("Hanoi")
```

Tool trả về:

```text
Observation:
31°C, light rain
```

Thông tin này sẽ ảnh hưởng trực tiếp tới Thought tiếp theo:

```text
Thought:
Weather is rainy, recommend indoor activities.
```

Nhờ cơ chế này Agent có thể thích nghi với môi trường thay vì chỉ dựa vào kiến thức tĩnh.

---

# IV. Future Improvements (5 Points)

## Scalability

Để triển khai trong môi trường thực tế:

- Tách Agent và Tool thành các service độc lập.
- Sử dụng hàng đợi bất đồng bộ (RabbitMQ/Kafka).
- Hỗ trợ nhiều Agent chạy song song.

Ví dụ:

```text
User
 |
 v
Gateway
 |
 +--> Search Agent
 |
 +--> Booking Agent
 |
 +--> Payment Agent
```

---

## Safety

Để tăng độ an toàn:

- Xây dựng Supervisor Agent để kiểm tra hành động trước khi thực thi.
- Giới hạn số lần gọi Tool.
- Kiểm soát quyền truy cập API.

Ví dụ:

```text
Agent
   |
   v
Supervisor
   |
Approve / Reject
   |
   v
Tool
```

---

## Performance

Khi số lượng Tool tăng lên:

- Sử dụng Vector Database để tìm Tool phù hợp.
- Cache kết quả các Tool thường dùng.
- Áp dụng Memory Storage để giảm số lần gọi LLM.

Công nghệ đề xuất:

- Redis Cache
- PostgreSQL
- Vector Database (Qdrant hoặc ChromaDB)
- Docker + Kubernetes
- Monitoring bằng Prometheus và Grafana

---

# Conclusion

Qua bài Lab 3, tôi hiểu rõ sự khác biệt giữa Chatbot truyền thống và ReAct Agent. Chatbot phù hợp với các câu hỏi đơn giản và phản hồi nhanh, trong khi ReAct Agent có khả năng suy luận từng bước, sử dụng công cụ bên ngoài và giải quyết các tác vụ phức tạp hơn. Việc xây dựng Agent cũng giúp tôi hiểu sâu hơn về Agent Loop, Tool Calling, Prompt Engineering và cơ chế Observation Feedback - những thành phần cốt lõi của các hệ thống AI Agent hiện đại.
