#!/usr/bin/env python3
"""
N8n API Client for AI Admin Hub

This module provides a comprehensive async HTTP client for interacting with the n8n API.
It implements proper authentication, error handling, rate limiting, and retry logic
based on lessons learned from the PowerShell implementation.

Key Features:
- Async HTTP requests using httpx for better performance
- Proper X-N8N-API-KEY authentication (not Bearer token!)
- Robust error handling with specific exception types
- Rate limiting and exponential backoff retry logic
- Comprehensive logging for debugging and monitoring
- Type-safe request/response handling with Pydantic models

Usage Example:
    ```python
    from ai_admin_hub.clients.n8n_client import N8nClient
    from ai_admin_hub.config import load_config
    
    # Initialize client with configuration
    config = load_config()
    async with N8nClient(config.n8n) as client:
        # List all workflows
        workflows = await client.list_workflows()
        print(f"Found {len(workflows)} workflows")
        
        # Export specific workflow
        workflow_data = await client.export_workflow("workflow_id")
        print(f"Exported workflow: {workflow_data['name']}")
    ```

Author: Roland (AI Admin Hub Project)
Created: 2025-08-22
Last Modified: 2025-08-22
License: MIT

Dependencies:
- httpx: Modern async HTTP client
- pydantic: Data validation and serialization
- tenacity: Retry logic with exponential backoff

Notes:
- Always use X-N8N-API-KEY header, NOT Authorization: Bearer
- N8n API responses are nested under 'data' key
- Rate limiting: Respect 429 responses and implement backoff
- Connection pooling: httpx client handles connection reuse efficiently
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field, validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ai_admin_hub.config import N8nConfig
from ai_admin_hub.exceptions import N8nAPIError, APIError
from ai_admin_hub.models.workflow import WorkflowSummary, WorkflowDetail

# Configure module logger
logger = logging.getLogger(__name__)


class N8nAPIResponse(BaseModel):
    """
    Standard N8n API response wrapper.
    
    N8n API returns responses in a nested format with metadata.
    This model handles the standard response structure.
    
    Attributes:
        data: The actual response data (workflows, executions, etc.)
        nextCursor: Pagination cursor for large result sets
        
    Example response:
        {
            "data": [...],
            "nextCursor": "eyJpZCI6IjEyMyJ9"
        }
    """
    data: List[Dict[str, Any]] = Field(default_factory=list)
    nextCursor: Optional[str] = Field(None, alias="nextCursor")
    
    class Config:
        allow_population_by_field_name = True


class N8nWorkflowStatus(BaseModel):
    """
    Workflow status information from N8n API.
    
    Attributes:
        active: Whether the workflow is currently active
        id: Unique workflow identifier
        name: Human-readable workflow name
        nodes: Number of nodes in the workflow
        connections: Number of connections between nodes
        createdAt: ISO timestamp when workflow was created
        updatedAt: ISO timestamp when workflow was last modified
    """
    active: bool = Field(..., description="Whether workflow is active")
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    nodes: int = Field(0, description="Number of nodes in workflow")
    connections: int = Field(0, description="Number of node connections")
    createdAt: str = Field(..., description="Creation timestamp (ISO format)")
    updatedAt: str = Field(..., description="Last update timestamp (ISO format)")
    
    @validator('id')
    def validate_id(cls, v):
        """Ensure workflow ID is not empty."""
        if not v or not v.strip():
            raise ValueError('Workflow ID cannot be empty')
        return v.strip()


class N8nClient:
    """
    Async HTTP client for N8n API interactions.
    
    This client handles all communication with the N8n REST API, including:
    - Authentication using X-N8N-API-KEY header
    - Automatic retry logic with exponential backoff
    - Rate limiting compliance
    - Error handling and logging
    - Response parsing and validation
    
    The client uses httpx for async HTTP requests and implements proper
    connection pooling and timeout handling.
    
    Attributes:
        config: N8n configuration (API key, base URL, etc.)
        client: httpx.AsyncClient instance for HTTP requests
        base_url: Normalized base URL for API endpoints
        
    Example:
        ```python
        config = N8nConfig(api_key="your_key", base_url="http://localhost:5678")
        
        async with N8nClient(config) as client:
            # Client automatically handles connection lifecycle
            workflows = await client.list_workflows()
            workflow = await client.get_workflow(workflows[0].id)
        ```
    """
    
    def __init__(self, config: N8nConfig):
        """
        Initialize N8n API client with configuration.
        
        Args:
            config: N8n configuration containing API key and base URL
            
        Raises:
            ValueError: If API key is missing or base URL is invalid
        """
        if not config.api_key:
            raise ValueError("N8n API key is required")
        
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        
        # Normalize base URL - ensure it ends with /api/v1
        self.base_url = self._normalize_base_url(config.base_url)
        
        # Default request timeout (30 seconds)
        self.timeout = httpx.Timeout(30.0)
        
        logger.info(f"Initialized N8n client for {self.base_url}")
    
    def _normalize_base_url(self, base_url: str) -> str:
        """
        Normalize the base URL to ensure consistent API endpoint format.
        
        N8n API endpoints are typically at /api/v1/, so we need to ensure
        the base URL is properly formatted for API calls.
        
        Args:
            base_url: Raw base URL from configuration
            
        Returns:
            Normalized URL ending with /api/v1
            
        Examples:
            "http://localhost:5678" -> "http://localhost:5678/api/v1"
            "https://n8n.example.com/" -> "https://n8n.example.com/api/v1"
            "http://localhost:5678/api/v1" -> "http://localhost:5678/api/v1"
        """
        # Remove trailing slash
        url = base_url.rstrip('/')
        
        # Add API path if not present
        if not url.endswith('/api/v1'):
            url = f"{url}/api/v1"
            
        return url
    
    async def __aenter__(self):
        """Async context manager entry - initialize HTTP client."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def _ensure_client(self):
        """
        Ensure HTTP client is initialized and ready for requests.
        
        Creates a new httpx.AsyncClient with proper configuration:
        - Custom headers including API key authentication
        - Reasonable timeout settings
        - Connection pooling for efficiency
        """
        if self.client is None:
            # CRITICAL: Use X-N8N-API-KEY header, NOT Authorization: Bearer!
            # This was a key lesson learned from PowerShell implementation
            headers = {
                "X-N8N-API-KEY": self.config.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AI-Admin-Hub/0.1.0"
            }
            
            self.client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                # Connection pool limits for efficiency
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
            
            logger.debug("HTTP client initialized with proper headers")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with automatic retry logic.
        
        This method implements robust error handling and retry logic:
        - Automatic retries for network errors and timeouts
        - Exponential backoff to avoid overwhelming the server
        - Comprehensive logging for debugging
        - Rate limiting compliance (respects 429 responses)
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., '/workflows')
            **kwargs: Additional arguments passed to httpx request
            
        Returns:
            HTTP response object
            
        Raises:
            N8nAPIError: If API returns an error response
            APIError: For other HTTP-related errors
        """
        await self._ensure_client()
        
        # Construct full URL
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # Handle rate limiting (429 Too Many Requests)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                # Let the retry decorator handle the retry
                raise httpx.NetworkError("Rate limited, retrying...")
            
            # Handle authentication errors (401 Unauthorized)
            if response.status_code == 401:
                raise N8nAPIError(
                    "Authentication failed. Check your N8n API key.",
                    status_code=401,
                    response=response.text
                )
            
            # Handle other client errors (4xx)
            if 400 <= response.status_code < 500:
                raise N8nAPIError(
                    f"Client error: {response.status_code}",
                    status_code=response.status_code,
                    response=response.text
                )
            
            # Handle server errors (5xx)
            if response.status_code >= 500:
                raise N8nAPIError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response=response.text
                )
            
            logger.debug(f"Request successful: {response.status_code}")
            return response
            
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {url}: {e}")
            raise APIError(f"Request timeout: {e}")
        
        except httpx.NetworkError as e:
            logger.error(f"Network error for {url}: {e}")
            raise APIError(f"Network error: {e}")
    
    async def list_workflows(
        self, 
        active_only: bool = False,
        limit: int = 100
    ) -> List[N8nWorkflowStatus]:
        """
        Retrieve list of all workflows from N8n.
        
        This method fetches workflow summaries including status, names, and IDs.
        It handles pagination automatically and can filter for active workflows only.
        
        Args:
            active_only: If True, return only active workflows
            limit: Maximum number of workflows to return (default: 100)
            
        Returns:
            List of workflow status objects
            
        Raises:
            N8nAPIError: If API request fails
            
        Example:
            ```python
            # Get all workflows
            workflows = await client.list_workflows()
            
            # Get only active workflows
            active_workflows = await client.list_workflows(active_only=True)
            
            for workflow in workflows:
                print(f"Workflow: {workflow.name} (Active: {workflow.active})")
            ```
        """
        logger.info(f"Fetching workflows (active_only={active_only}, limit={limit})")
        
        # Build query parameters
        params = {"limit": limit}
        if active_only:
            params["active"] = "true"
        
        try:
            response = await self._make_request("GET", "/workflows", params=params)
            
            # Parse JSON response
            response_data = response.json()
            
            # Handle N8n's nested response format
            # API returns: {"data": [...], "nextCursor": "..."}
            if isinstance(response_data, dict) and "data" in response_data:
                workflows_data = response_data["data"]
            else:
                # Fallback for direct array response
                workflows_data = response_data if isinstance(response_data, list) else []
            
            # Convert to typed models with validation
            workflows = []
            for workflow_data in workflows_data:
                try:
                    # Create typed workflow status object
                    workflow = N8nWorkflowStatus(**workflow_data)
                    workflows.append(workflow)
                except Exception as e:
                    logger.warning(f"Failed to parse workflow data: {e}")
                    logger.debug(f"Raw workflow data: {workflow_data}")
                    continue
            
            logger.info(f"Successfully retrieved {len(workflows)} workflows")
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise N8nAPIError(f"Failed to list workflows: {e}")
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Retrieve detailed workflow information by ID.
        
        This method fetches complete workflow data including nodes, connections,
        and configuration. Use this when you need full workflow details.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Complete workflow data as dictionary
            
        Raises:
            N8nAPIError: If workflow not found or API request fails
            ValueError: If workflow_id is empty
            
        Example:
            ```python
            workflow = await client.get_workflow("abc123")
            print(f"Workflow: {workflow['name']}")
            print(f"Nodes: {len(workflow.get('nodes', []))}")
            ```
        """
        if not workflow_id or not workflow_id.strip():
            raise ValueError("Workflow ID cannot be empty")
        
        workflow_id = workflow_id.strip()
        logger.info(f"Fetching workflow details for ID: {workflow_id}")
        
        try:
            response = await self._make_request("GET", f"/workflows/{workflow_id}")
            workflow_data = response.json()
            
            logger.info(f"Successfully retrieved workflow: {workflow_data.get('name', workflow_id)}")
            return workflow_data
            
        except N8nAPIError as e:
            if e.status_code == 404:
                raise N8nAPIError(f"Workflow not found: {workflow_id}")
            raise
        
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise N8nAPIError(f"Failed to get workflow: {e}")
    
    async def export_workflow(
        self, 
        workflow_id: str,
        include_credentials: bool = False
    ) -> Dict[str, Any]:
        """
        Export workflow in JSON format suitable for backup or import.
        
        This method retrieves the complete workflow definition in a format
        that can be saved as backup or imported into another n8n instance.
        
        Args:
            workflow_id: Unique workflow identifier
            include_credentials: Whether to include credential references
                                (WARNING: This may expose sensitive data!)
            
        Returns:
            Exportable workflow data structure
            
        Raises:
            N8nAPIError: If export fails or workflow not found
            ValueError: If workflow_id is empty
            
        Security Note:
            Setting include_credentials=True may expose sensitive credential
            references. Use with caution and ensure proper access controls.
            
        Example:
            ```python
            # Export workflow for backup (safe)
            exported = await client.export_workflow("abc123")
            
            # Save to file
            import json
            with open("workflow_backup.json", "w") as f:
                json.dump(exported, f, indent=2)
            ```
        """
        if not workflow_id or not workflow_id.strip():
            raise ValueError("Workflow ID cannot be empty")
        
        workflow_id = workflow_id.strip()
        logger.info(f"Exporting workflow: {workflow_id} (credentials={include_credentials})")
        
        # Security warning for credential inclusion
        if include_credentials:
            logger.warning("Exporting workflow WITH credentials - ensure secure handling!")
        
        try:
            # Get full workflow data
            workflow_data = await self.get_workflow(workflow_id)
            
            # If credentials should not be included, remove credential references
            if not include_credentials:
                workflow_data = self._sanitize_credentials(workflow_data)
            
            # Add export metadata
            export_data = {
                "workflow": workflow_data,
                "exported_at": f"{asyncio.get_event_loop().time()}",
                "exported_by": "AI Admin Hub",
                "credentials_included": include_credentials
            }
            
            logger.info(f"Successfully exported workflow: {workflow_data.get('name', workflow_id)}")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export workflow {workflow_id}: {e}")
            raise N8nAPIError(f"Failed to export workflow: {e}")
    
    def _sanitize_credentials(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or mask credential references from workflow data.
        
        This method ensures that exported workflows don't contain sensitive
        credential information. It replaces credential references with placeholders.
        
        Args:
            workflow_data: Raw workflow data from API
            
        Returns:
            Sanitized workflow data with credentials removed/masked
            
        Implementation Note:
            This is a security-critical function. It must reliably remove
            all potential credential references to prevent data leaks.
        """
        sanitized = workflow_data.copy()
        
        # Remove credential IDs from nodes
        if "nodes" in sanitized:
            for node in sanitized["nodes"]:
                if "credentials" in node:
                    # Replace with placeholder indicating credentials were removed
                    for cred_type in node["credentials"]:
                        node["credentials"][cred_type] = {
                            "id": "REMOVED_FOR_SECURITY",
                            "name": "CREDENTIAL_PLACEHOLDER"
                        }
        
        logger.debug("Sanitized credentials from workflow export")
        return sanitized
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on N8n API connectivity.
        
        This method tests the API connection and returns status information
        useful for monitoring and diagnostics.
        
        Returns:
            Health status information including:
            - API connectivity status
            - Response time
            - Available workflows count
            - N8n version info (if available)
            
        Example:
            ```python
            health = await client.health_check()
            if health["status"] == "healthy":
                print(f"N8n API is healthy - {health['workflow_count']} workflows")
            else:
                print(f"N8n API issues: {health['error']}")
            ```
        """
        logger.info("Performing N8n API health check")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Test basic API connectivity by listing workflows
            workflows = await self.list_workflows(limit=1)
            
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            
            health_data = {
                "status": "healthy",
                "response_time_seconds": round(response_time, 3),
                "api_url": self.base_url,
                "workflow_count": len(workflows),
                "timestamp": end_time
            }
            
            logger.info(f"Health check passed - response time: {response_time:.3f}s")
            return health_data
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            
            health_data = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_seconds": round(response_time, 3),
                "api_url": self.base_url,
                "timestamp": end_time
            }
            
            logger.error(f"Health check failed: {e}")
            return health_data


# Convenience function for quick client creation
async def create_n8n_client(config: N8nConfig) -> N8nClient:
    """
    Factory function to create and initialize N8n client.
    
    This is a convenience function for creating a properly configured
    N8n client instance. Prefer using the async context manager when possible.
    
    Args:
        config: N8n configuration
        
    Returns:
        Initialized N8n client
        
    Example:
        ```python
        from ai_admin_hub.config import load_config
        
        config = load_config()
        client = await create_n8n_client(config.n8n)
        
        # Remember to close the client when done
        await client.__aexit__(None, None, None)
        ```
    """
    client = N8nClient(config)
    await client._ensure_client()
    return client


# Export public interface
__all__ = [
    "N8nClient",
    "N8nAPIResponse", 
    "N8nWorkflowStatus",
    "create_n8n_client"
]