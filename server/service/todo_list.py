import datetime

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import session, joinedload, Session

from entity import models, schemas
from service import groups as group_service


def get_todo_list(
        group_id: int, current_user: models.User, db: session, from_date_str: str, to_date_str: str
) -> list[schemas.TodoItemsGroupByDate]:
    db_items = get_todo_list_base(group_id, current_user, db, from_date_str=from_date_str, to_date_str=to_date_str)
    # 按日期分组
    result = list()
    current_key = ""
    for db_item in db_items:
        if current_key != (temp_key := db_item.start_time.strftime("%Y-%m-%d")) or current_key == "":
            current_key = temp_key
            result.append(schemas.TodoItemsGroupByDate(key=current_key, value=list()))
        else:
            current_key = db_item.start_time.strftime("%Y-%m-%d")
        result[-1].value.append(db_item)
    return result


def get_undetermined_todo_list(group_id: int, current_user: models.User, db: Session):
    return get_todo_list_base(group_id, current_user, db, is_undetermined=True)


def get_todo_list_base(
        group_id: int, current_user: models.User, db: session, from_date_str: str = '', to_date_str: str = '',
        is_undetermined: bool = False
) -> list[schemas.TodoItemsGroupByDate]:
    if group_id != 0 and not group_service.is_user_in_group(current_user.id, group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    query = db.query(models.TodoList).filter(models.TodoList.group_id == group_id)
    if is_undetermined:
        query = query.filter(models.TodoList.is_undetermined == True)
    else:
        next_date_str = (datetime.datetime.strptime(to_date_str, "%Y-%m-%d") + datetime.timedelta(days=1)
                         ).strftime("%Y-%m-%d")
        query = query.filter(models.TodoList.start_time.between(from_date_str, next_date_str))
    if group_id == 0:
        query = query.filter(models.TodoList.user_id == current_user.id)
    db_items = query.options(joinedload(models.TodoList.done_user), joinedload(models.TodoList.creator)).order_by(
        desc(models.TodoList.id), desc(models.TodoList.id)).all()
    return db_items


def create_todo_item(item: schemas.TodoItemCreate, current_user: models.User, db: session) -> models.TodoList:
    if item.group_id != 0 and not group_service.is_user_in_group(current_user.id, item.group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    if item.is_undetermined:
        item.start_time = None
        item.end_time = None
        item.is_all_day = False
    elif item.is_all_day:
        item.start_time = item.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        item.end_time = item.end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    db_item = models.TodoList(**item.dict(), user_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_todo_item(item: schemas.TodoItemUpdate, current_user: models.User, db: session):
    db_item = db.query(models.TodoList).get(item.id)
    if not db_item:
        raise HTTPException(404, "事项不存在")
    if db_item.group_id != 0 and not group_service.is_user_in_group(current_user.id, db_item.group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    if db_item.group_id == 0 and db_item.user_id != current_user.id:
        raise HTTPException(403, detail="无权限修改他人事项")
    if item.is_undetermined:
        item.start_time = None
        item.end_time = None
        item.is_all_day = False
    elif item.is_all_day:
        item.start_time = item.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        item.end_time = item.end_time.replace(hour=0, minute=0, second=0, microsecond=0)

    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    return db_item


def delete_todo_item(item_id: int, current_user: models.User, db: session):
    db_item = db.query(models.TodoList).get(item_id)
    if not db_item:
        raise HTTPException(404, "事项不存在")
    if db_item.group_id != 0 and not group_service.is_user_in_group(current_user.id, db_item.group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    if db_item.group_id == 0 and db_item.user_id != current_user.id:
        raise HTTPException(403, detail="无权限删除他人事项")
    db.delete(db_item)
    db.commit()


def done_todo_item(req: schemas.DoneTodoItem, current_user: models.User, db: session):
    db_item: models.TodoList = db.query(models.TodoList).get(req.id)
    if not db_item:
        raise HTTPException(404, "事项不存在")
    if db_item.group_id != 0 and not group_service.is_user_in_group(current_user.id, db_item.group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    if db_item.group_id == 0 and db_item.user_id != current_user.id:
        raise HTTPException(403, detail="无权限完成他人事项")
    db_item.is_done = True
    db_item.done_result = req.done_result
    db_item.done_by = current_user.id
    db.commit()


def cancel_todo_item(item_id: int, current_user: models, db: session):
    db_item: models.TodoList = db.query(models.TodoList).get(item_id)
    if db_item.group_id != 0 and not group_service.is_user_in_group(current_user.id, db_item.group_id, db):
        raise HTTPException(403, detail="请先加入此团队")
    if not db_item:
        raise HTTPException(404, "事项不存在")
    if db_item.group_id == 0 and db_item.user_id != current_user.id:
        raise HTTPException(403, detail="无权限取消他人事项")
    db_item.is_done = False
    db_item.done_by = None
    db.commit()
