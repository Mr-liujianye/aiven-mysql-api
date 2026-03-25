from fastapi import FastAPI, HTTPException, Depends, Header, Query
from pydantic import BaseModel
import pymysql
import pymysql.cursors
import os

app = FastAPI(title="Aiven MySQL 学生成绩 CRUD API", version="1.0")

# ========== 数据库连接配置（去掉 SSL 配置，适配全开放 IP） ==========
DB_CONFIG = {
    "host": "mysql-51db351-curry-d6b4.i.aivencloud.com",
    "port": 21039,
    "user": "avnadmin",
    "password": "AVNS_90tKPf7s6mpw8-I1JUY",
    "database": "defaultdb",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "auth_plugin": "mysql_native_password"  # 新增这一行
    # 完全删除 SSL 相关配置，让 pymysql 自动协商连接
}

# ========== API 鉴权（不变） ==========
def verify_api_key(api_key: str = Header(None)):
    if api_key != "your_secure_key_123":
        raise HTTPException(status_code=401, detail="无效的 API Key，请填写 your_secure_key_123")
    return api_key

# ========== 数据模型（含学号/工号字段） ==========
class Student(BaseModel):
    name: str
    student_no: str  # 学号（纯数字）
    score: int
    class_id: int
    teacher_id: int

class Teacher(BaseModel):
    name: str
    subject: str
    teacher_no: str  # 工号（T开头）

# ========== 核心查询（权限过滤） ==========
@app.get("/api/students", summary="查询学生成绩（支持权限过滤）")
def get_students(
    api_key: str = Depends(verify_api_key),
    student_no: str = Query(None, description="学生学号（仅查单个学生）"),
    teacher_no: str = Query(None, description="老师工号（仅查授课班级）")
):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 基础关联查询 SQL（保留你的核心逻辑）
            base_sql = """
                SELECT s.id, s.name AS 学生, s.student_no AS 学号, s.score AS 成绩, 
                       c.name AS 班级, t.name AS 老师, t.teacher_no AS 老师工号
                FROM students s 
                JOIN classes c ON s.class_id = c.id 
                JOIN teachers t ON s.teacher_id = t.id
            """
            # 学生权限：仅查自己
            if student_no:
                sql = f"{base_sql} WHERE s.student_no = %s"
                cursor.execute(sql, (student_no,))
            # 老师权限：仅查授课班级
            elif teacher_no:
                sql = f"{base_sql} WHERE t.teacher_no = %s"
                cursor.execute(sql, (teacher_no,))
            # 无过滤（测试用）
            else:
                cursor.execute(base_sql)
            
            results = cursor.fetchall()
        return {"code": 200, "data": results, "msg": "查询成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 新增学生（适配学号） ==========
@app.post("/api/students", summary="新增学生")
def add_student(student: Student, api_key: str = Depends(verify_api_key)):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO students (name, student_no, score, class_id, teacher_id) 
                VALUES (%s, %s, %s, %s, %s)
            """, (student.name, student.student_no, student.score, student.class_id, student.teacher_id))
        connection.commit()
        return {"code": 200, "data": {"id": cursor.lastrowid, **student.dict()}, "msg": "新增学生成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增失败：{str(e)}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 修改学生成绩 ==========
@app.put("/api/students/{student_id}", summary="修改学生成绩")
def update_student_score(student_id: int, score: int, api_key: str = Depends(verify_api_key)):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 检查学生是否存在
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="学生不存在")
            
            # 修改成绩
            cursor.execute("UPDATE students SET score = %s WHERE id = %s", (score, student_id))
        connection.commit()
        return {"code": 200, "data": {"学生ID": student_id, "新成绩": score}, "msg": "修改成功"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改失败：{str(e)}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 删除学生 ==========
@app.delete("/api/students/{student_id}", summary="删除学生")
def delete_student(student_id: int, api_key: str = Depends(verify_api_key)):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 检查学生是否存在
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="学生不存在")
            
            # 删除学生
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        connection.commit()
        return {"code": 200, "data": {"学生ID": student_id}, "msg": "删除成功"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 健康检查 ==========
@app.get("/", summary="API 健康检查")
def health_check():
    return {"message": "CRUD API 运行正常！访问 /docs 测试所有接口"}

# ========== Render 启动配置 ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
