import os 
import datetime
from fastapi import APIRouter, UploadFile, HTTPException, Form
from loguru import logger
from app.api.utils import generate_random_string
from app.config import settings, celery_app, redis_client

router = APIRouter(tags=['API'])

@router.post("/api/upload/")
async def upload_file(file: UploadFile,expiration_minutes: int = Form(...)):
    try:
        file_content = await file.read()

        max_file_size = 5 * 1024 * 1024

        if len(file_content) > max_file_size:
            raise HTTPException(status_code=413, detail="Превышен максимальный размер файла (5 МБ).")
        upload_dir = settings.UPLOAD_DIR
        total_size = sum(os.path.getsize(os.path.join(upload_dir, f)) for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)))

        max_total_size = 100 * 1024 * 1024  
        if total_size + len(file_content) > max_total_size:
            raise HTTPException(status_code=507, detail="Превышен общий лимит размера файлов (100 МБ). Освободите место и повторите попытку.")
        start_file_name = file.filename
        
        file_extension = os.path.splitext(file.filename)[1]
        file_id = generate_random_string(12)
        dell_id = generate_random_string(12)
        file_path = os.path.join(settings.UPLOAD_DIR, file_id + file_extension)
        with open(file_path, "wb") as f:
            f.write(file_content)

        expiration_seconds = expiration_minutes * 60
        expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expiration_seconds)    

        celery_app.send_task('delete_file_scheduled',args=[file_id,dell_id],countdown=expiration_seconds)

        download_url = f"{settings.BASE_URL}/files/{file_id + file_extension}"
        view_url = f"{settings.BASE_URL}/view_file/{file_id}"

        redis_key = f"file:{file_id}"
        redis_client.hmset(redis_key,{
            "file_path": file_path,
            "dell_id": dell_id,
            "download_url": download_url,
            "expiration_time": int(expiration_time.timestamp()),
            "start_file_name": start_file_name})
        
        return {
            "message": "Файл успешно загружен",
            "file_id": file_id,
            "dell_id": dell_id,
            "download_url": download_url,
            "view_url": view_url,
            "expiration_time": expiration_time.isoformat(),
            "expiration_seconds": expiration_seconds
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")

@router.delete("/delete/{file_id}/{dell_id}")
async def delete_file(file_id: str, dell_id: str):
    redis_key = f"file:{file_id}"
    file_info = redis_client.hgetall(redis_key)

    if not file_info:
        raise HTTPException(status_code=404, detail="Файл не найден")
    dell_id_redis = file_info.get(b"dell_id").decode()
    if dell_id_redis != dell_id:
        raise HTTPException(status_code=403, detail="Не совпадает айди удаления с айди удаления файла")
    
    file_path = file_info.get(b"file_path").decode()

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл {file_path} успешно удален!")
        else:
            logger.warning(f"Файл {file_path} не найден.")

        redis_client.delete(redis_key)
        return {"message": "Файл успешно удален и запись в Redis очищена!"}
    
    except OSError as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")
