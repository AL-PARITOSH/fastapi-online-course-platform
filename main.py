from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status, Request
from pydantic import BaseModel, Field, EmailStr
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

# =========================
# Logging & Middleware
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("learnhub")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"{method} {path} -> {response.status_code} in {duration_ms:.2f}ms"
        )
        return response


# =========================
# Tags & App Metadata
# =========================

tags_metadata = [
    {
        "name": "public",
        "description": "Public endpoints for health checks and basic information.",
    },
    {
        "name": "courses",
        "description": "Manage LearnHub courses (list, CRUD, filter, search, sort, pagination, browse).",
    },
    {
        "name": "enrollments",
        "description": "Create and manage student enrollments, including search, sort, and pagination.",
    },
    {
        "name": "wishlist",
        "description": "Wishlist operations and the multi-step workflow from wishlist to enrollments.",
    },
]

app = FastAPI(
    title="LearnHub Online Courses API",
    description="A FastAPI backend for an online learning platform. "
    "Includes courses, enrollments, wishlist workflow, and advanced browse/search/sort/pagination.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

app.add_middleware(RequestLoggingMiddleware)

# =========================
# In-memory Data
# =========================

courses = [
    {
        "id": 1,
        "title": "Python for Data Science",
        "instructor": "Dr. Rao",
        "category": "Data Science",
        "level": "Beginner",
        "price": 0,
        "seats_left": 10,
    },
    {
        "id": 2,
        "title": "Full-Stack Web Development",
        "instructor": "Anita Sharma",
        "category": "Web Dev",
        "level": "Intermediate",
        "price": 4999,
        "seats_left": 5,
    },
    {
        "id": 3,
        "title": "UI/UX Design Basics",
        "instructor": "Rohan Mehta",
        "category": "Design",
        "level": "Beginner",
        "price": 1999,
        "seats_left": 8,
    },
    {
        "id": 4,
        "title": "Advanced Machine Learning",
        "instructor": "Dr. Sen",
        "category": "Data Science",
        "level": "Advanced",
        "price": 6999,
        "seats_left": 3,
    },
    {
        "id": 5,
        "title": "DevOps with Docker & Kubernetes",
        "instructor": "Priya Verma",
        "category": "DevOps",
        "level": "Intermediate",
        "price": 5999,
        "seats_left": 6,
    },
    {
        "id": 6,
        "title": "Frontend with React",
        "instructor": "Vikram Singh",
        "category": "Web Dev",
        "level": "Beginner",
        "price": 2999,
        "seats_left": 4,
    },
]

enrollments: List[dict] = []
enrollment_counter: int = 1

wishlist: List[dict] = []

# =========================
# Pydantic Models
# =========================


class Course(BaseModel):
    id: int
    title: str
    instructor: str
    category: str
    level: str
    price: int
    seats_left: int


class CoursesListResponse(BaseModel):
    total: int
    total_seats_available: int
    courses: List[Course]


class CoursesPageResponse(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
    courses: List[Course]


class CoursesBrowseResponse(BaseModel):
    keyword: Optional[str]
    category: Optional[str]
    level: Optional[str]
    max_price: Optional[int]
    sort_by: Optional[str]
    order: str
    page: int
    limit: int
    total_items: int
    total_pages: int
    courses: List[Course]


class EnrollRequest(BaseModel):
    student_name: str = Field(..., min_length=2)
    course_id: int = Field(..., gt=0)
    email: EmailStr = Field(..., min_length=5)
    payment_method: str = Field(default="card")
    coupon_code: str = Field(default="")
    gift_enrollment: bool = Field(default=False)
    recipient_name: str = Field(default="")


class EnrollmentResponse(BaseModel):
    enrollment_id: int
    student_name: str
    recipient_name: Optional[str]
    gift_enrollment: bool
    email: str
    payment_method: str
    course_id: int
    course_title: str
    instructor: str
    original_price: int
    discounts_applied: List[dict]
    final_fee: int


class EnrollmentsPageResponse(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
    enrollments: List[EnrollmentResponse]


class NewCourse(BaseModel):
    title: str = Field(..., min_length=2)
    instructor: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    level: str = Field(..., min_length=2)
    price: int = Field(..., ge=0)
    seats_left: int = Field(..., gt=0)


class WishlistEnrollRequest(BaseModel):
    student_name: str = Field(..., min_length=2)
    payment_method: str = Field(default="card")


# =========================
# Helper Functions (plain)
# =========================


def find_course(course_id: int) -> Optional[dict]:
    for course in courses:
        if course["id"] == course_id:
            return course
    return None


def calculate_enrollment_fee(
    price: int, seats_left: int, coupon_code: str
) -> dict:
    original_price = price
    discount_details = []

    if seats_left > 5:
        early_discount = int(price * 0.10)
        price -= early_discount
        discount_details.append(
            {"type": "early_bird_10", "amount": early_discount}
        )

    coupon_code = coupon_code.strip().upper()
    if coupon_code == "STUDENT20":
        coupon_discount = int(price * 0.20)
        price -= coupon_discount
        discount_details.append(
            {"type": "STUDENT20_20pct", "amount": coupon_discount}
        )
    elif coupon_code == "FLAT500":
        coupon_discount = 500 if price >= 500 else price
        price -= coupon_discount
        discount_details.append(
            {"type": "FLAT500", "amount": coupon_discount}
        )

    final_fee = max(price, 0)

    return {
        "original_price": original_price,
        "final_fee": final_fee,
        "discounts": discount_details,
    }


def filter_courses_logic(
    category: Optional[str],
    level: Optional[str],
    max_price: Optional[int],
    has_seats: Optional[bool],
) -> List[dict]:
    filtered = courses
    if category is not None:
        filtered = [
            c
            for c in filtered
            if c["category"].lower() == category.lower()
        ]
    if level is not None:
        filtered = [
            c for c in filtered if c["level"].lower() == level.lower()
        ]
    if max_price is not None:
        filtered = [c for c in filtered if c["price"] <= max_price]
    if has_seats is not None:
        if has_seats:
            filtered = [c for c in filtered if c["seats_left"] > 0]
        else:
            filtered = [c for c in filtered if c["seats_left"] <= 0]
    return filtered


# =========================
# Public & Health
# =========================


@app.get("/", tags=["public"])
def home():
    return {"message": "Welcome to LearnHub Online Courses"}


@app.get("/health", tags=["public"])
def health_check():
    return {"status": "ok", "service": "learnhub-api"}


@app.get("/instructors", tags=["public"])
def list_instructors():
    stats = {}
    for c in courses:
        name = c["instructor"]
        stats.setdefault(
            name, {"instructor": name, "courses": 0}
        )
        stats[name]["courses"] += 1
    return {"total": len(stats), "instructors": list(stats.values())}


# =========================
# Courses GETs (fixed paths first)
# =========================


@app.get("/courses", response_model=CoursesListResponse, tags=["courses"])
def get_courses():
    total = len(courses)
    total_seats_available = sum(c["seats_left"] for c in courses)
    return {
        "total": total,
        "total_seats_available": total_seats_available,
        "courses": courses,
    }


@app.get("/courses/summary", tags=["courses"])
def get_courses_summary():
    total_courses = len(courses)
    free_courses_count = sum(1 for c in courses if c["price"] == 0)

    if not courses:
        most_expensive_course = None
    else:
        most_expensive_course = max(
            courses, key=lambda c: c["price"]
        )

    total_seats = sum(c["seats_left"] for c in courses)

    category_counts = {}
    low_seat_alerts = []
    for c in courses:
        cat = c["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if c["seats_left"] <= 2:
            low_seat_alerts.append(
                {
                    "course_id": c["id"],
                    "title": c["title"],
                    "seats_left": c["seats_left"],
                }
            )

    return {
        "total_courses": total_courses,
        "free_courses_count": free_courses_count,
        "most_expensive_course": most_expensive_course,
        "total_seats": total_seats,
        "count_by_category": category_counts,
        "low_seat_alerts": low_seat_alerts,
    }


@app.get("/courses/filter", tags=["courses"])
def filter_courses(
    category: Optional[str] = None,
    level: Optional[str] = None,
    max_price: Optional[int] = None,
    has_seats: Optional[bool] = None,
):
    filtered = filter_courses_logic(
        category=category,
        level=level,
        max_price=max_price,
        has_seats=has_seats,
    )
    return {"total": len(filtered), "courses": filtered}


@app.get("/courses/search", tags=["courses"])
def search_courses(keyword: str = Query(..., min_length=1)):
    keyword_lower = keyword.lower()
    matches = [
        c
        for c in courses
        if keyword_lower in c["title"].lower()
        or keyword_lower in c["instructor"].lower()
        or keyword_lower in c["category"].lower()
    ]
    return {"keyword": keyword, "total_found": len(matches), "courses": matches}


@app.get("/courses/sort", tags=["courses"])
def sort_courses(
    sort_by: str = Query("price"),
    order: str = Query("asc"),
):
    valid_sort_by = {"price", "title", "seats_left"}
    if sort_by not in valid_sort_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Must be one of {valid_sort_by}",
        )

    if order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order. Must be 'asc' or 'desc'",
        )

    reverse = order == "desc"
    sorted_courses = sorted(
        courses, key=lambda c: c[sort_by], reverse=reverse
    )

    return {
        "sort_by": sort_by,
        "order": order,
        "total": len(sorted_courses),
        "courses": sorted_courses,
    }


@app.get(
    "/courses/page",
    response_model=CoursesPageResponse,
    tags=["courses"],
)
def paginate_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1),
):
    total_items = len(courses)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number out of range",
        )

    start = (page - 1) * limit
    end = start + limit
    page_items = courses[start:end]

    return {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "courses": page_items,
    }


@app.get(
    "/courses/browse",
    response_model=CoursesBrowseResponse,
    tags=["courses"],
)
def browse_courses(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    max_price: Optional[int] = None,
    sort_by: Optional[str] = Query(None),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1),
):
    result = courses

    if keyword:
        kw = keyword.lower()
        result = [
            c
            for c in result
            if kw in c["title"].lower()
            or kw in c["instructor"].lower()
            or kw in c["category"].lower()
        ]

    if category:
        result = [
            c
            for c in result
            if c["category"].lower() == category.lower()
        ]

    if level:
        result = [
            c for c in result if c["level"].lower() == level.lower()
        ]

    if max_price is not None:
        result = [c for c in result if c["price"] <= max_price]

    if sort_by:
        valid_sort_by = {"price", "title", "seats_left"}
        if sort_by not in valid_sort_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by. Must be one of {valid_sort_by}",
            )
        if order not in {"asc", "desc"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order. Must be 'asc' or 'desc'",
            )
        reverse = order == "desc"
        result = sorted(
            result, key=lambda c: c[sort_by], reverse=reverse
        )

    total_items = len(result)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number out of range",
        )

    start = (page - 1) * limit
    end = start + limit
    page_items = result[start:end]

    return {
        "keyword": keyword,
        "category": category,
        "level": level,
        "max_price": max_price,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "courses": page_items,
    }


# dynamic course route LAST
@app.get("/courses/{course_id}", tags=["courses"])
def get_course_by_id(course_id: int):
    course = find_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


# =========================
# Enrollments basic GET
# =========================


@app.get("/enrollments", tags=["enrollments"])
def get_enrollments():
    return {"total": len(enrollments), "enrollments": enrollments}


# =========================
# Q6–10: POST + helpers
# =========================


@app.post(
    "/enrollments",
    status_code=status.HTTP_201_CREATED,
    response_model=EnrollmentResponse,
    tags=["enrollments"],
)
def create_enrollment(request: EnrollRequest):
    global enrollment_counter

    course = find_course(request.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if course["seats_left"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No seats left for this course",
        )

    if request.gift_enrollment and not request.recipient_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_name is required when gift_enrollment is True",
        )

    fee_info = calculate_enrollment_fee(
        price=course["price"],
        seats_left=course["seats_left"],
        coupon_code=request.coupon_code,
    )

    course["seats_left"] -= 1

    enrollment_record = {
        "enrollment_id": enrollment_counter,
        "student_name": request.student_name,
        "recipient_name": request.recipient_name
        if request.gift_enrollment
        else None,
        "gift_enrollment": request.gift_enrollment,
        "email": request.email,
        "payment_method": request.payment_method,
        "course_id": course["id"],
        "course_title": course["title"],
        "instructor": course["instructor"],
        "original_price": fee_info["original_price"],
        "discounts_applied": fee_info["discounts"],
        "final_fee": fee_info["final_fee"],
    }

    enrollments.append(enrollment_record)
    enrollment_counter += 1

    return enrollment_record


# =========================
# Q11–13: Course CRUD
# =========================


@app.post(
    "/courses",
    status_code=status.HTTP_201_CREATED,
    response_model=Course,
    tags=["courses"],
)
def create_course(new_course: NewCourse):
    for c in courses:
        if c["title"].lower() == new_course.title.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course with this title already exists",
            )

    new_id = max(c["id"] for c in courses) + 1 if courses else 1
    course_dict = {
        "id": new_id,
        "title": new_course.title,
        "instructor": new_course.instructor,
        "category": new_course.category,
        "level": new_course.level,
        "price": new_course.price,
        "seats_left": new_course.seats_left,
    }
    courses.append(course_dict)
    return course_dict


@app.put("/courses/{course_id}", tags=["courses"])
def update_course(
    course_id: int,
    price: Optional[int] = Query(default=None),
    seats_left: Optional[int] = Query(default=None),
):
    course = find_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if price is not None:
        if price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="price must be >= 0",
            )
        course["price"] = price

    if seats_left is not None:
        if seats_left < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="seats_left must be >= 0",
            )
        course["seats_left"] = seats_left

    return course


@app.delete("/courses/{course_id}", tags=["courses"])
def delete_course(course_id: int):
    course = find_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    for e in enrollments:
        if e["course_id"] == course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete course with enrolled students",
            )

    for idx, c in enumerate(courses):
        if c["id"] == course_id:
            del courses[idx]
            break

    return {"message": "Course deleted successfully"}


# =========================
# Q14–15: Wishlist workflow
# =========================


@app.post("/wishlist/add", tags=["wishlist"])
def add_to_wishlist(
    student_name: str = Query(..., min_length=2),
    course_id: int = Query(..., gt=0),
):
    course = find_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    for item in wishlist:
        if (
            item["student_name"].lower()
            == student_name.lower()
            and item["course_id"] == course_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course already in wishlist for this student",
            )

    wishlist_item = {
        "student_name": student_name,
        "course_id": course_id,
        "course_title": course["title"],
        "price": course["price"],
    }
    wishlist.append(wishlist_item)
    return wishlist_item


@app.get("/wishlist", tags=["wishlist"])
def get_wishlist():
    total_value = sum(item["price"] for item in wishlist)
    return {
        "total_items": len(wishlist),
        "total_value": total_value,
        "items": wishlist,
    }


@app.delete("/wishlist/remove/{course_id}", tags=["wishlist"])
def remove_from_wishlist(
    course_id: int,
    student_name: str = Query(..., min_length=2),
):
    global wishlist
    original_len = len(wishlist)
    wishlist = [
        item
        for item in wishlist
        if not (
            item["course_id"] == course_id
            and item["student_name"].lower()
            == student_name.lower()
        )
    ]
    if len(wishlist) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found for this student and course",
        )
    return {"message": "Removed from wishlist"}


@app.post("/wishlist/enroll-all", tags=["wishlist", "enrollments"])
def enroll_all_from_wishlist(body: WishlistEnrollRequest):
    global enrollment_counter, wishlist

    student_name = body.student_name
    payment_method = body.payment_method

    student_wishlist = [
        item
        for item in wishlist
        if item["student_name"].lower() == student_name.lower()
    ]

    if not student_wishlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No wishlist items found for this student",
        )

    created_enrollments = []
    grand_total_fee = 0

    remaining_wishlist = []
    for item in wishlist:
        if item not in student_wishlist:
            remaining_wishlist.append(item)

    for item in student_wishlist:
        course = find_course(item["course_id"])
        if not course or course["seats_left"] <= 0:
            continue

        fee_info = calculate_enrollment_fee(
            price=course["price"],
            seats_left=course["seats_left"],
            coupon_code="",
        )

        course["seats_left"] -= 1

        enrollment_record = {
            "enrollment_id": enrollment_counter,
            "student_name": student_name,
            "recipient_name": None,
            "gift_enrollment": False,
            "email": "",
            "payment_method": payment_method,
            "course_id": course["id"],
            "course_title": course["title"],
            "instructor": course["instructor"],
            "original_price": fee_info["original_price"],
            "discounts_applied": fee_info["discounts"],
            "final_fee": fee_info["final_fee"],
        }
        enrollments.append(enrollment_record)
        created_enrollments.append(enrollment_record)
        grand_total_fee += fee_info["final_fee"]
        enrollment_counter += 1

    wishlist = remaining_wishlist

    return {
        "student_name": student_name,
        "total_enrolled": len(created_enrollments),
        "grand_total_fee": grand_total_fee,
        "enrollments": created_enrollments,
    }


# =========================
# Enrollments search/sort/page
# =========================


@app.get("/enrollments/search", tags=["enrollments"])
def search_enrollments(student_name: str = Query(..., min_length=1)):
    name_lower = student_name.lower()
    matches = [
        e
        for e in enrollments
        if name_lower in e["student_name"].lower()
    ]
    return {
        "student_name": student_name,
        "total_found": len(matches),
        "enrollments": matches,
    }


@app.get("/enrollments/sort", tags=["enrollments"])
def sort_enrollments(order: str = Query("asc")):
    if order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order. Must be 'asc' or 'desc'",
        )

    reverse = order == "desc"
    sorted_enrollments = sorted(
        enrollments, key=lambda e: e["final_fee"], reverse=reverse
    )
    return {
        "order": order,
        "total": len(sorted_enrollments),
        "enrollments": sorted_enrollments,
    }


@app.get(
    "/enrollments/page",
    response_model=EnrollmentsPageResponse,
    tags=["enrollments"],
)
def paginate_enrollments(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1),
):
    total_items = len(enrollments)
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number out of range",
        )

    start = (page - 1) * limit
    end = start + limit
    page_items = enrollments[start:end]

    return {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "enrollments": page_items,
    }
