"""News API routes"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, Any, List

from app.config import get_settings

router = APIRouter(prefix="/api/news", tags=["news"])
settings = get_settings()


@router.get("/today")
async def get_today_news() -> Dict[str, Any]:
    """Get today's news meta data.
    
    Returns:
        Today's featured articles and metadata from articles_meta.json
        
    Raises:
        HTTPException: 404 if file not found, 500 for file read errors
    """
    try:
        # Get current date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        # Get environment-specific path
        data_path = settings.get_news_data_path()
        
        # Build path to articles_meta.json
        meta_file = Path(data_path) / today / "articles_meta.json"
        
        # Check if file exists
        if not meta_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No news data found for date {today} at {meta_file}"
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
    
    Args:
        offset: Starting index
        limit: Number of articles to return
        
    Returns:
        Articles list with pagination info
        
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
        
        # Check if file exists
        if not index_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No articles index found for date {today} at {index_file}"
            )
        
        # Read articles index
        with open(index_file, 'r', encoding='utf-8') as f:
            all_articles = json.load(f)
        
        # Sort by importance_score (descending)
        sorted_articles = sorted(
            all_articles,
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
        
        # Check if file exists
        if not detail_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No news data found for date {today} at {detail_file}"
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

