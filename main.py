from fastapi import FastAPI, HTTPException, Depends, Header
import pymysql
import pymysql.cursors
import os

# 初始化 FastAPI 应用
app = FastAPI(title="Aiven MySQL 学生成绩查询 API", version="1.0")

# ========== 你的 Aiven MySQL 连接配置（无需修改） ==========
DB_CONFIG = {
    "host": "mysql-51db351-curry-d6b4.i.aivencloud.com",
    "port": 21039,
    "user": "avnadmin",
    "password": "AVNS_6Hq73KP_8kBwOVGpIof",
    "database": "defaultdb",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,  # 返回字典格式结果
    "ssl": {"ssl_mode": "REQUIRED"}             # 适配 Aiven SSL 强制要求
}

# ========== API 鉴权（防止接口被恶意调用） ==========
def verify_api_key(api_key: str = Header(None)):
    # 调用接口时必须携带这个密钥，和火山智能体配置保持一致
    if api_key != "your_secure_key_123":
        raise HTTPException(status_code=401, detail="无效的 API Key，请填写 your_secure_key_123")
    return api_key

# ========== 初始化数据库表和测试数据 ==========
@app.post("/init_db", summary="创建班级/教师/学生表 + 插入测试数据")
def init_database(api_key: str = Depends(verify_api_key)):
    try:
        # 建立数据库连接
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 1. 创建班级表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(20) NOT NULL
                )
            """)
            
            # 2. 创建教师表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(20) NOT NULL,
                    subject VARCHAR(20) NOT NULL
                )
            """)
            
            # 3. 创建学生表（关联班级/教师）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(20) NOT NULL,
                    score INT NOT NULL,
                    class_id INT,
                    teacher_id INT,
                    FOREIGN KEY (class_id) REFERENCES classes(id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id)
                )
            """)
            
            # 4. 插入测试数据（IGNORE 避免重复插入）
            cursor.execute("INSERT IGNORE INTO classes (name) VALUES ('一年级一班')")
            cursor.execute("INSERT IGNORE INTO teachers (name, subject) VALUES ('张老师', '数学')")
            cursor.execute("INSERT IGNORE INTO students (name, score, class_id, teacher_id) VALUES ('小明', 98, 1, 1)")
        
        # 提交事务（必须执行，否则数据不会写入）
        connection.commit()
        return {"code": 200, "message": "数据库初始化成功！已创建表并插入测试数据"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败：{str(e)}")
    finally:
        # 确保数据库连接关闭
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 综合查询：学生+成绩+班级+老师 ==========
@app.get("/api/students", summary="查询学生成绩（关联班级/教师信息）")
def get_student_scores(api_key: str = Depends(verify_api_key)):
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 执行你提供的关联查询 SQL
            cursor.execute("""
                SELECT s.name AS 学生, s.score AS 成绩, c.name AS 班级, t.name AS 老师 
                FROM students s 
                JOIN classes c ON s.class_id = c.id 
                JOIN teachers t ON s.teacher_id = t.id
            """)
            # 获取查询结果（列表格式）
            results = cursor.fetchall()
        
        return {"code": 200, "data": results, "msg": "查询成功"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# ========== 根路径：API 健康检查 ==========
@app.get("/", summary="验证 API 是否正常运行")
def health_check():
    return {"message": "Aiven MySQL API 运行正常！访问 /docs 查看接口文档"}

# ========== Render 启动配置（必须保留） ==========
if __name__ == "__main__":
    import uvicorn
    # 读取 Render 自动分配的端口（不能写死端口号）
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
