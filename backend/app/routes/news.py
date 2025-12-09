"""News API routes"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, Any, List

from app.config import get_settings

router = APIRouter(prefix="/api/news", tags=["news"])
settings = get_settings()


def get_latest_available_date(data_path: str) -> str:
    """Find the latest date with valid news data (articles_meta.json exists).
    
    Args:
        data_path: Base path to news data directory
        
    Returns:
        Latest available date in YYYYMMDD format, or None if no data found
    """
    base = Path(data_path)
    if not base.exists():
        return None
    
    # Get all date directories sorted in descending order
    date_dirs = sorted([d for d in base.iterdir() if d.is_dir() and d.name.isdigit()], 
                       key=lambda x: x.name, reverse=True)
    
    for date_dir in date_dirs:
        meta_file = date_dir / "articles_meta.json"
        if meta_file.exists() and meta_file.stat().st_size > 10:  # Check file exists and has content
            return date_dir.name
    
    return None


@router.get("/today")
async def get_today_news() -> Dict[str, Any]:
    """Get today's news meta data (with fallback to latest available date).
    
    Returns:
        Today's (or latest available) featured articles and metadata from articles_meta.json
        
    Raises:
        HTTPException: 404 if no data found, 500 for file read errors
    """
    try:
        # Get current date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        # Get environment-specific path
        data_path = settings.get_news_data_path()
        
        # Build path to articles_meta.json
        meta_file = Path(data_path) / today / "articles_meta.json"
        
        # Check if today's file exists with valid content
        if not meta_file.exists() or meta_file.stat().st_size <= 10:
            # Fallback: find latest available date
            latest_date = get_latest_available_date(data_path)
            if latest_date:
                meta_file = Path(data_path) / latest_date / "articles_meta.json"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No news data found in {data_path}"
                )
        
        # Read and return JSON
        with open(meta_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read news data: {str(e)}"
        )


@router.get("/articles")
async def get_articles(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return")
) -> Dict[str, Any]:
    """Get articles list for infinite scroll.
    
    Excludes featured articles to avoid duplication with /api/news/today endpoint.
    
    Args:
        offset: Starting index (after excluding featured articles)
        limit: Number of articles to return
        
    Returns:
        Articles list with pagination info (featured articles excluded)
        
    Raises:
        HTTPException: 404 if file not found, 500 for file read errors
    """
    try:
        # Get current date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        # Get environment-specific path
        data_path = settings.get_news_data_path()
        
        # Build path to articles_index.json
        index_file = Path(data_path) / today / "articles_index.json"
        
        # Check if file exists with valid content, fallback if needed
        if not index_file.exists() or index_file.stat().st_size <= 10:
            latest_date = get_latest_available_date(data_path)
            if latest_date:
                today = latest_date
                index_file = Path(data_path) / today / "articles_index.json"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No articles index found in {data_path}"
                )
        
        # Read articles index
        with open(index_file, 'r', encoding='utf-8') as f:
            all_articles = json.load(f)
        
        # Get featured articles IDs to exclude them
        meta_file = Path(data_path) / today / "articles_meta.json"
        featured_ids = set()
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
                featured_articles = meta_data.get('featured_articles', [])
                featured_ids = {article.get('id') for article in featured_articles if 'id' in article}
        
        # Filter out featured articles
        non_featured_articles = [
            article for article in all_articles
            if article.get('id') not in featured_ids
        ]
        
        # Sort by importance_score (descending)
        sorted_articles = sorted(
            non_featured_articles,
            key=lambda x: x.get('importance_score', 0),
            reverse=True
        )
        
        # Apply pagination
        total = len(sorted_articles)
        articles = sorted_articles[offset:offset + limit]
        
        return {
            "articles": articles,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read articles: {str(e)}"
        )


@router.get("/article/{article_id}")
async def get_article_detail(article_id: int) -> Dict[str, Any]:
    """Get article detail by ID.
    
    Args:
        article_id: Article ID to retrieve
        
    Returns:
        Article detail with full content
        
    Raises:
        HTTPException: 404 if file/article not found, 500 for file read errors
    """
    try:
        # Get current date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        # Get environment-specific path
        data_path = settings.get_news_data_path()
        
        # Build path to articles_detail.json
        detail_file = Path(data_path) / today / "articles_detail.json"
        
        # Check if file exists with valid content, fallback if needed
        if not detail_file.exists() or detail_file.stat().st_size <= 10:
            latest_date = get_latest_available_date(data_path)
            if latest_date:
                detail_file = Path(data_path) / latest_date / "articles_detail.json"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No news data found in {data_path}"
                )
        
        # Read JSON
        with open(detail_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get article by ID (JSON keys are strings)
        article_key = str(article_id)
        if article_key not in data:
            raise HTTPException(
                status_code=404,
                detail=f"Article {article_id} not found"
            )
        
        return data[article_key]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read article detail: {str(e)}"
        )


        data_path = settings.get_news_data_path()
        
        # Build path to articles_detail.json
        detail_file = Path(data_path) / today / "articles_detail.json"
        
        # Check if file exists with valid content, fallback if needed
        if not detail_file.exists() or detail_file.stat().st_size <= 10:
            latest_date = get_latest_available_date(data_path)
            if latest_date:
                detail_file = Path(data_path) / latest_date / "articles_detail.json"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No news data found in {data_path}"
                )
        
        # Read JSON
        with open(detail_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get article by ID (JSON keys are strings)
        article_key = str(article_id)
        if article_key not in data:
            raise HTTPException(
                status_code=404,
                detail=f"Article {article_id} not found"
            )
        
        return data[article_key]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read article detail: {str(e)}"
        )

