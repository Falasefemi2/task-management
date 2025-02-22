from fastapi import APIRouter, Depends, HTTPException
from model import Task, User
from schema import TaskCreate, TaskCreateResponse, TaskResponse, TaskUpdate
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import or_
from auth import get_current_user
from typing import List


router = APIRouter()

@router.post("/create-task", response_model=TaskCreateResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Route to create a task"""
    existing_task = db.query(Task).filter(Task.title == task.title, Task.owner_id == current_user.id).first()
    if existing_task:
        raise HTTPException(status_code=400, detail='Task with this title already exists for this user')
    
    new_task = Task(
        title = task.title,
        description = task.description,
        completed = task.completed,
        owner_id = current_user.id
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return TaskCreateResponse(
        id=new_task.id, 
        title=new_task.title,
        description=new_task.description,
        completed=new_task.completed,
        owner_id=new_task.owner_id,
        message="Task created successfully"
    )

    
@router.get("/get-task", response_model=List[TaskResponse])
async def get_task(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Route to get all task"""
    tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()
    
    return tasks

@router.get("/get-task/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Route to get a specific task by ID for the authenticated user"""

    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()

    # If the task is not found, raise a 404 error
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task 


@router.put("/update-task/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Route to update a specific task by Id for the authenticated user"""
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    
        # If the task is not found, raise a 404 error
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_update.title is not None:
        task.title = task_update.title
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.completed is not None:
        task.completed = task_update.completed

    db.commit()
    db.refresh(task)
    
    return task

@router.delete("/delete-task/{task_id}", response_model=dict)
async def delete_task(task_id: int,db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Route to delete a specific task"""
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"message": f"Task {task_id} deleted successfully"}    


@router.patch("/{task_id}/toggle-complete", response_model=TaskResponse)
async def toggle_task_complete(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle task for completion"""
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.completed = not task.completed
    db.commit()
    db.refresh(task)
    
    return task


@router.get("/completed", response_model=List[TaskResponse])
async def get_completed_task(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all completed task"""
    task = db.query(Task).filter(Task.owner_id == current_user.id, Task.completed.is_(True)).all()
    return task

@router.get("/incomplete", response_model=List[TaskResponse])
async def get_incomplete_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all incomplete tasks"""
    tasks = db.query(Task).filter(
        Task.owner_id == current_user.id,
        Task.completed.is_(False)
    ).all()
    return tasks


@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    query: str,
    case_sensitive: bool = False,
    search_by: str = "all",  # Add parameter to control search field
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search tasks by title and/or description
    Parameters:
        - query: Search term
        - case_sensitive: If True, performs case-sensitive search. Default is False
        - search_by: Options are 'all', 'title', or 'description'. Default is 'all'
    """
    base_query = db.query(Task).filter(Task.owner_id == current_user.id)
    
    if search_by not in ["all", "title", "description"]:
        raise HTTPException(
            status_code=400,
            detail="search_by must be 'all', 'title', or 'description'"
        )
    
    try:
        if case_sensitive:
            if search_by == "title":
                tasks = base_query.filter(Task.title.like(f"%{query}%")).all()
            elif search_by == "description":
                tasks = base_query.filter(Task.description.like(f"%{query}%")).all()
            else:  # search_by == "all"
                tasks = base_query.filter(
                    or_(
                        Task.title.like(f"%{query}%"),
                        Task.description.like(f"%{query}%")
                    )
                ).all()
        else:
            if search_by == "title":
                tasks = base_query.filter(Task.title.ilike(f"%{query}%")).all()
            elif search_by == "description":
                tasks = base_query.filter(Task.description.ilike(f"%{query}%")).all()
            else:  # search_by == "all"
                tasks = base_query.filter(
                    or_(
                        Task.title.ilike(f"%{query}%"),
                        Task.description.ilike(f"%{query}%")
                    )
                ).all()

        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found matching your search criteria in {search_by}"
            )
        
        return tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during search: {str(e)}"
        ) from e

@router.get("/paginated", response_model=List[TaskResponse])
async def get_paginated_task(
    skip: int =  0,
    limit: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task with pagination"""
    tasks = db.query(Task).filter(
        Task.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return tasks

@router.get("/stats")
async def get_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task statistics"""
    total_tasks = db.query(Task).filter(Task.owner_id == current_user.id).count()
    completed_tasks = db.query(Task).filter(
        Task.owner_id == current_user.id,
        Task.completed.is_(True)
    ).count()
    incomplete_tasks = total_tasks - completed_tasks
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "incomplete_tasks": incomplete_tasks,
        "completion_rate": f"{(completed_tasks/total_tasks * 100) if total_tasks > 0 else 0:.2f}%"
    }