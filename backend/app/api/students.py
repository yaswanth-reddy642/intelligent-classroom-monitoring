"""Student record management API endpoints with photo enrollment."""

import logging
import os
import time
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

PRIVACY_NOTICE = (
    "This system performs automated classroom video analysis. "
    "Student photos are used for identity mapping to track suspicious activities."
)


class StudentRecord(BaseModel):
    name: str
    roll_number: str
    department: str = ""
    section: str = ""
    semester: int = 0
    mobile_number: str = ""
    parent_mobile: str = ""
    email: str = ""


class StudentUpdateRecord(BaseModel):
    name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    semester: Optional[int] = None
    mobile_number: Optional[str] = None
    parent_mobile: Optional[str] = None
    email: Optional[str] = None


def _normalize_csv_header(h: str) -> str:
    """Normalize user CSV column headers to canonical schema field names."""
    clean = h.strip().lower().replace(" ", "_").replace(".", "").replace("-", "_")
    mapping = {
        "student_name": "name",
        "full_name": "name",
        "name": "name",
        "roll_no": "roll_number",
        "rollno": "roll_number",
        "roll": "roll_number",
        "roll_number": "roll_number",
        "reg_no": "roll_number",
        "registration_no": "roll_number",
        "registration_number": "roll_number",
        "dept": "department",
        "department": "department",
        "branch": "department",
        "sec": "section",
        "section": "section",
        "sem": "semester",
        "semester": "semester",
        "mobile": "mobile_number",
        "mobile_no": "mobile_number",
        "mobile_number": "mobile_number",
        "student_mobile": "mobile_number",
        "phone": "mobile_number",
        "contact": "mobile_number",
        "parent_mobile": "parent_mobile",
        "parent_phone": "parent_mobile",
        "parent_contact": "parent_mobile",
        "father_mobile": "parent_mobile",
        "mother_mobile": "parent_mobile",
        "email": "email",
        "email_id": "email",
        "student_email": "email",
    }
    return mapping.get(clean, clean)


@router.get("/students/sample-csv")
async def download_sample_csv():
    """Download a template CSV file for student enrollment with all supported fields."""
    from fastapi.responses import Response

    sample_csv = (
        "Name,Roll Number,Department,Section,Semester,Student Mobile,Parent Mobile,Email\n"
        "Rahul Sharma,21CS101,Computer Science,A,6,+919876543210,+919876543211,rahul.sharma@example.edu\n"
        "Priya Patel,21CS102,Computer Science,A,6,+919876543212,+919876543213,priya.patel@example.edu\n"
        "Ananya Singh,21CS103,Computer Science,B,6,+919876543214,+919876543215,ananya.singh@example.edu\n"
        "Vikram Verma,21CS104,Computer Science,B,6,+919876543216,+919876543217,vikram.verma@example.edu\n"
        "Sneha Reddy,21IT201,Information Technology,A,6,+919876543218,+919876543219,sneha.reddy@example.edu\n"
    )

    return Response(
        content=sample_csv,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=student_enrollment_template.csv"
        },
    )


@router.post("/students/upload-csv")
async def upload_students_csv(file: UploadFile = File(...)):
    """Upload a CSV file to bulk enroll student records with all fields."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Invalid file format. Please upload a .csv file.")

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(400, f"Could not decode CSV file: {e}. Please ensure it is saved in UTF-8 format.")

    import csv
    import io

    try:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
    except Exception as e:
        raise HTTPException(400, f"Malformed CSV content: {e}")

    if not rows:
        raise HTTPException(400, "CSV file is completely empty.")

    raw_headers = rows[0]
    normalized_headers = [_normalize_csv_header(h) for h in raw_headers]

    if "name" not in normalized_headers or "roll_number" not in normalized_headers:
        raise HTTPException(
            400,
            f"Missing required columns in CSV header. Found: {raw_headers}. At least 'Name' and 'Roll Number' are required.",
        )

    from backend.app.database.mongodb import get_db
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection not available.")

    total_rows = len(rows) - 1
    inserted_count = 0
    updated_count = 0
    errors = []
    processed_students = []

    for idx, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue

        row_dict = {}
        for h_idx, col_name in enumerate(normalized_headers):
            if h_idx < len(row):
                row_dict[col_name] = row[h_idx].strip()

        name = row_dict.get("name", "")
        roll_number = row_dict.get("roll_number", "")

        if not name or not roll_number:
            errors.append({"row": idx, "reason": "Name and Roll Number cannot be empty."})
            continue

        try:
            semester = int(row_dict.get("semester", 0)) if row_dict.get("semester") else 0
        except ValueError:
            semester = 0

        student_data = {
            "name": name,
            "roll_number": roll_number,
            "department": row_dict.get("department", ""),
            "section": row_dict.get("section", ""),
            "semester": semester,
            "mobile_number": row_dict.get("mobile_number", ""),
            "parent_mobile": row_dict.get("parent_mobile", ""),
            "email": row_dict.get("email", ""),
            "is_active": True,
            "updated_at": time.time(),
        }

        existing = await db.students.find_one({"roll_number": roll_number})
        if existing:
            await db.students.update_one(
                {"roll_number": roll_number},
                {"$set": student_data},
            )
            updated_count += 1
            student_data["student_id"] = existing.get("student_id")
        else:
            student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
            student_data["student_id"] = student_id
            student_data["photo_url"] = ""
            student_data["created_at"] = time.time()
            await db.students.insert_one(student_data)
            inserted_count += 1

        processed_students.append({
            "name": name,
            "roll_number": roll_number,
            "department": student_data["department"],
            "student_id": student_data.get("student_id"),
        })

    # Trigger roster refresh in face matcher if live pipeline is active
    try:
        from backend.app.main import inference_service
        if inference_service and hasattr(inference_service, "_pipeline"):
            all_students = await db.students.find({"is_active": True}).to_list(length=500)
            inference_service._pipeline.face_matcher.set_students_from_db(all_students)
            logger.info("Synchronized live face matcher with updated student roster.")
    except Exception as e:
        logger.debug(f"Could not refresh live pipeline face matcher: {e}")

    logger.info(f"CSV student upload complete: {inserted_count} new, {updated_count} updated, {len(errors)} errors.")
    return {
        "success": True,
        "filename": file.filename,
        "total_rows": total_rows,
        "inserted": inserted_count,
        "updated": updated_count,
        "errors": errors,
        "students": processed_students,
        "message": f"Successfully processed {total_rows} row(s): {inserted_count} new enrolled, {updated_count} updated, {len(errors)} error(s).",
    }


@router.get("/students/privacy")
async def get_privacy_notice():
    return {"privacy_notice": PRIVACY_NOTICE}


@router.get("/students")
async def get_students():
    try:
        from backend.app.database.repositories import StudentRepository
        students = await StudentRepository.find_all()
        for s in students:
            s["_id"] = str(s["_id"])
        return {
            "students": students,
            "total": await StudentRepository.count(),
            "privacy_notice": PRIVACY_NOTICE,
        }
    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return {"students": [], "total": 0, "privacy_notice": PRIVACY_NOTICE}


@router.post("/students")
async def create_student(record: StudentRecord):
    try:
        from backend.app.database.repositories import StudentRepository

        student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
        student_data = {
            "student_id": student_id,
            "name": record.name,
            "roll_number": record.roll_number,
            "department": record.department,
            "section": record.section,
            "semester": record.semester,
            "mobile_number": record.mobile_number,
            "parent_mobile": record.parent_mobile,
            "email": record.email,
            "photo_url": "",
            "created_at": time.time(),
            "is_active": True,
        }
        await StudentRepository.insert(student_data)
        return {
            "success": True,
            "student_id": student_id,
            "name": record.name,
            "roll_number": record.roll_number,
            "message": f"Student record created for {record.name}",
        }
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        raise HTTPException(500, f"Failed to create student record: {e}")


@router.post("/students/{roll_number}/photo")
async def upload_student_photo(roll_number: str, file: UploadFile = File(...)):
    """Upload a photo for a student. Used for identity mapping."""
    from backend.app.database.mongodb import get_db
    db = get_db()

    student = await db.students.find_one({"roll_number": roll_number})
    if not student:
        raise HTTPException(404, f"Student {roll_number} not found")

    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file.filename or "photo.jpg")[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {', '.join(allowed)}")

    # Save photo
    safe_name = f"{roll_number}{ext}"
    save_path = os.path.join(PHOTOS_DIR, safe_name)

    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        photo_url = f"/uploads/photos/{safe_name}"
        await db.students.update_one(
            {"roll_number": roll_number},
            {"$set": {"photo_url": photo_url}},
        )
        logger.info(f"Photo uploaded for {roll_number}: {save_path}")

        # Synchronize live pipeline face matcher with new photo
        try:
            from backend.app.main import inference_service
            if inference_service and hasattr(inference_service, "_pipeline"):
                inference_service._pipeline.face_matcher.refresh_roster()
                logger.info(f"Refreshed face matcher embeddings after photo upload for {roll_number}")
        except Exception as e:
            logger.debug(f"Could not refresh live pipeline face matcher: {e}")

        return {
            "success": True,
            "roll_number": roll_number,
            "photo_url": photo_url,
            "size_kb": round(len(content) / 1024, 1),
        }
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        raise HTTPException(500, f"Photo upload failed: {e}")


@router.get("/students/{roll_number}")
async def get_student(roll_number: str):
    from backend.app.database.mongodb import get_db
    db = get_db()
    student = await db.students.find_one({"roll_number": roll_number})
    if not student:
        raise HTTPException(404, f"Student with roll_number {roll_number} not found")
    student["_id"] = str(student["_id"])
    return student


@router.put("/students/{roll_number}")
@router.patch("/students/{roll_number}")
async def update_student(roll_number: str, record: StudentUpdateRecord):
    """Update an existing student's details in the database."""
    from backend.app.database.mongodb import get_db
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection unavailable")

    student = await db.students.find_one({"roll_number": roll_number})
    if not student:
        # Fallback check by student_id
        student = await db.students.find_one({"student_id": roll_number})
        if not student:
            raise HTTPException(404, f"Student with roll number {roll_number} not found")

    old_roll = student.get("roll_number", roll_number)
    update_data = {}

    if record.name is not None and record.name.strip():
        update_data["name"] = record.name.strip()
    if record.department is not None:
        update_data["department"] = record.department.strip()
    if record.section is not None:
        update_data["section"] = record.section.strip()
    if record.semester is not None:
        try:
            update_data["semester"] = int(record.semester)
        except (ValueError, TypeError):
            update_data["semester"] = 0
    if record.mobile_number is not None:
        update_data["mobile_number"] = record.mobile_number.strip()
    if record.parent_mobile is not None:
        update_data["parent_mobile"] = record.parent_mobile.strip()
    if record.email is not None:
        update_data["email"] = record.email.strip()

    # Handle roll number change
    new_roll = record.roll_number.strip() if record.roll_number else None
    if new_roll and new_roll != old_roll:
        # Check for conflict with existing students
        conflict = await db.students.find_one({
            "roll_number": new_roll,
            "_id": {"$ne": student["_id"]}
        })
        if conflict:
            raise HTTPException(
                400,
                f"Roll number {new_roll} is already registered to another student ({conflict.get('name', 'N/A')})"
            )
        update_data["roll_number"] = new_roll

        # If student has an existing photo, rename it to reflect new roll number
        if student.get("photo_url"):
            old_filename = os.path.basename(student["photo_url"])
            old_photo_path = os.path.join(PHOTOS_DIR, old_filename)
            if os.path.exists(old_photo_path):
                ext = os.path.splitext(old_filename)[1]
                new_filename = f"{new_roll}{ext}"
                new_photo_path = os.path.join(PHOTOS_DIR, new_filename)
                try:
                    os.rename(old_photo_path, new_photo_path)
                    update_data["photo_url"] = f"/uploads/photos/{new_filename}"
                    logger.info(f"Renamed photo {old_photo_path} -> {new_photo_path}")
                except Exception as pe:
                    logger.warning(f"Could not rename photo file during roll update: {pe}")

        # Update associated alert history with the new roll number
        try:
            await db.alerts.update_many(
                {"roll_number": old_roll},
                {"$set": {"roll_number": new_roll, "student_display_id": f"ST-{new_roll}"}}
            )
        except Exception as ae:
            logger.debug(f"Could not update historical alerts with new roll: {ae}")

    # Also update student name in alerts if name changed
    if "name" in update_data and update_data["name"] != student.get("name"):
        try:
            await db.alerts.update_many(
                {"roll_number": update_data.get("roll_number", old_roll)},
                {"$set": {"student_name": update_data["name"]}}
            )
        except Exception as ae:
            logger.debug(f"Could not update historical alerts with new name: {ae}")

    if not update_data:
        student["_id"] = str(student["_id"])
        return {"success": True, "message": "No changes requested", "student": student}

    update_data["updated_at"] = time.time()
    await db.students.update_one({"_id": student["_id"]}, {"$set": update_data})

    updated_student = await db.students.find_one({"_id": student["_id"]})
    if updated_student:
        updated_student["_id"] = str(updated_student["_id"])

    # Synchronize face matcher in live pipeline
    try:
        from backend.app.main import inference_service
        if inference_service and hasattr(inference_service, "_pipeline"):
            all_students = await db.students.find({"is_active": True}).to_list(length=500)
            inference_service._pipeline.face_matcher.set_students_from_db(all_students)
            inference_service._pipeline.face_matcher.refresh_roster()
            logger.info("Synchronized live face matcher with updated student roster.")
    except Exception as e:
        logger.debug(f"Could not refresh live pipeline face matcher: {e}")

    logger.info(f"Student updated successfully: {old_roll} -> {update_data.get('roll_number', old_roll)}")
    return {
        "success": True,
        "message": f"Student {updated_student.get('name')} details updated successfully",
        "student": updated_student,
    }


@router.delete("/students/{roll_number}")
async def delete_student(roll_number: str):
    try:
        from backend.app.database.mongodb import get_db
        db = get_db()

        # Delete photo if exists
        student = await db.students.find_one({"roll_number": roll_number})
        if student and student.get("photo_url"):
            photo_path = os.path.join(PHOTOS_DIR, os.path.basename(student["photo_url"]))
            if os.path.exists(photo_path):
                os.remove(photo_path)

        result = await db.students.delete_one({"roll_number": roll_number})
        if result.deleted_count == 0:
            raise HTTPException(404, f"Student with roll_number {roll_number} not found")
        return {"success": True, "message": f"Removed student record {roll_number}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        raise HTTPException(500, f"Failed to delete student record: {e}")
