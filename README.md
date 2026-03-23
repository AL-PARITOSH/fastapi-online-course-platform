# FASTAPI-ONLINE-COURSE-PLATFORM

# LearnHub Online Courses API

A FastAPI-based backend for an online learning platform, built as an assignment project.  
It demonstrates clean API design, Pydantic models, business logic, and advanced querying over in‑memory data.

---

---

## Project Overview

**LearnHub Online Courses API** simulates the backend of an online course platform.

It exposes endpoints to:

- List, filter, search, sort, paginate, and browse courses  
- Create and manage enrollments with discounts and gift options  
- Maintain a wishlist and convert wishlist items into enrollments  
- Search, sort, and paginate enrollments for reporting

All data is kept in memory for simplicity (no database), making it ideal for learning and demonstration.

---

## Features

- FastAPI application with tagged routes and automatic interactive docs (Swagger UI)
- Request logging middleware with execution time measurement
- Strong Pydantic models for requests and responses
- In-memory collections for courses, enrollments, and wishlist items
- Course operations:
  - List all courses with aggregate stats
  - Get course by ID
  - Filter by category, level, price, seat availability
  - Search, sort, pagination, and advanced “browse” with combined options
  - Basic CRUD: create, update, delete courses (with safety checks)
- Enrollment operations:
  - Create enrollment with validation and discount logic
  - Gift enrollments to another person
  - Search/sort/paginate enrollments
- Wishlist workflow:
  - Add/remove items
  - View wishlist totals
  - Enroll all wishlist items for a given student in one step

---

## Tech Stack

- **Language:** Python 3.x  
- **Framework:** FastAPI  
- **Data validation:** Pydantic  
- **Server:** Uvicorn (ASGI)  
- **Logging & middleware:** standard `logging` + custom middleware

---

## API Modules

### Public

- `GET /`
  - Simple welcome message.
- `GET /health`
  - Health check status.
- `GET /instructors`
  - Aggregated instructor list with course counts.

---

### Courses

Core course operations:

- `GET /courses`
  - Returns all courses plus:
    - `total`
    - `total_seats_available`
- `GET /courses/summary`
  - High-level stats:
    - total courses
    - free course count
    - most expensive course
    - total seats available
    - counts by category
    - low-seat alerts

Filtering and browsing:

- `GET /courses/filter`
  - Query params:
    - `category` (optional)
    - `level` (optional)
    - `max_price` (optional)
    - `has_seats` (optional, bool)
- `GET /courses/search`
  - Query param:
    - `keyword` (required) — matches title, instructor, or category.
- `GET /courses/sort`
  - Query params:
    - `sort_by` in `{price, title, seats_left}`
    - `order` in `{asc, desc}`
- `GET /courses/page`
  - Pagination over all courses:
    - `page` (default 1)
    - `limit` (default 3)
- `GET /courses/browse`
  - Combined keyword search, filters, sorting, and pagination.

CRUD:

- `GET /courses/{course_id}`
  - Fetch single course or 404 if not found.
- `POST /courses`
  - Create new course (with unique title requirement).
- `PUT /courses/{course_id}`
  - Update `price` and/or `seats_left` via query parameters.
- `DELETE /courses/{course_id}`
  - Delete course if there are no enrollments for it.

---

### Enrollments

- `GET /enrollments`
  - Simple list (for early questions).
- `POST /enrollments`
  - Creates a new enrollment:
    - Validates course existence and seat availability
    - Applies discount logic
    - Supports gift enrollments (`gift_enrollment` + `recipient_name`)
    - Decrements `seats_left` on the course
- `GET /enrollments/search`
  - Query param `student_name`, substring match.
- `GET /enrollments/sort`
  - Sort by `final_fee` (`order = asc | desc`).
- `GET /enrollments/page`
  - Paginate enrollments: `page`, `limit`.

---

### Wishlist

- `POST /wishlist/add`
  - Query params:
    - `student_name`
    - `course_id`
  - Adds course to that student’s wishlist if not already present.
- `GET /wishlist`
  - Returns all wishlist items plus:
    - `total_items`
    - `total_value`
- `DELETE /wishlist/remove/{course_id}`
  - Removes a course from a specific student’s wishlist.
- `POST /wishlist/enroll-all`
  - Body:
    - `student_name`
    - `payment_method`
  - Takes all wishlist items for that student and:
    - Creates enrollments (if seats available)
    - Applies discount logic without coupons
    - Decrements course seats
    - Clears those wishlist items

---

## Business Logic Highlights

- **Discount system**
  - Early-bird: if `seats_left > 5` → 10% off.
  - Coupons:
    - `STUDENT20` → 20% off (after early-bird).
    - `FLAT500` → flat 500 off (not below 0).
  - Final fee is always non-negative.

- **Gift enrollments**
  - When `gift_enrollment = true`, `recipient_name` is required.
  - Stored in enrollment record and returned in the response.

- **Safety checks**
  - Cannot enroll when `seats_left <= 0`.
  - Cannot delete a course if any enrollment uses it.
  - Cannot add duplicate wishlist item for the same student and course.
  - Pagination returns “page out of range” when appropriate.

---

## How to Run

   ```bash
   git clone https://github.com/your-username/learnhub-fastapi.git
   cd learnhub-fastapi
Create virtual environment (optional but recommended)

bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
Install dependencies

bash
pip install fastapi uvicorn pydantic email-validator
Run the server

bash
uvicorn main:app --reload
Open the API docs

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc
