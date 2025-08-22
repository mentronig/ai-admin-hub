#!/usr/bin/env python3
"""
Test Suite for N8n API Client

Comprehensive test suite covering all functionality of the N8nClient class.
Tests include both unit tests with mocked responses and integration tests
that can optionally run against a real N8n instance.

Test Categories:
- Unit Tests: Mock HTTP responses to test client logic
- Integration Tests: Optional tests against real N8n API (requires configuration)
- Error Handling Tests: Verify proper exception handling and retry logic
- Authentication Tests: Verify correct header format and API key handling

Usage:
    # Run all tests with mocked responses
    pytest tests/clients/test_n8n_client.py
    
    # Run with integration tests (requires .env.test configuration)
    pytest tests/clients/test_n8n_client.py --integration
    
    # Run with coverage reporting
    pytest tests/clients/test_n8n_client.py --cov=ai_admin_hub.clients.n8n_client

Author: Roland (AI Admin Hub Project)
Created: 2025-08-22
License: MIT

Dependencies:
- pytest: Test framework
- pytest-asyncio: Async test support
- httpx: For mocking HTTP responses
- respx: HTTP request mocking library
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

import httpx
import respx
from pydantic import ValidationError

from ai_admin_hub.clients.n8n_client import (
    N8nClient,
    N8nAPIResponse,
    N8nWorkflowStatus,
    create_n8n_client
)
from ai_admin_hub.config import N8nConfig
from ai_admin_hub.exceptions import N8nAPIError, APIError


class TestN8nConfig:
    """Test configuration validation and setup."""
    
    def test_valid_config(self):
        """Test creating valid N8n configuration."""
        config = N8nConfig(
            api_key="test_api_key_123",
            base_url="http://localhost:5678",
            workflow_id="test_workflow_id"
        )
        
        assert config.api_key == "test_api_key_123"
        assert config.base_url == "http://localhost:5678"
        assert config.workflow_id == "test_workflow_id"
    
    def test_missing_api_key(self):
        """Test that missing API key raises validation error."""
        with pytest.raises(ValidationError):
            N8nConfig(api_key="", base_url="http://localhost:5678")
    
    def test_invalid_base_url(self):
        """Test that invalid base URL raises validation error."""
        with pytest.raises(ValidationError):
            N8nConfig(api_key="test_key", base_url="invalid_url")


class TestN8nWorkflowStatus:
    """Test workflow status model validation."""
    
    def test_valid_workflow_status(self):
        """Test creating valid workflow status."""
        status = N8nWorkflowStatus(
            active=True,
            id="workflow_123",
            name="Test Workflow",
            nodes=5,
            connections=4,
            createdAt="2025-08-22T10:00:00Z",
            updatedAt="2025-08-22T12:00:00Z"
        )
        
        assert status.active is True
        assert status.id == "workflow_123"
        assert status.name == "Test Workflow"
        assert status.nodes == 5
        assert status.connections == 4
    
    def test_empty_workflow_id(self):
        """Test that empty workflow ID raises validation error."""
        with pytest.raises(ValidationError):
            N8nWorkflowStatus(
                active=True,
                id="",  # Empty ID should fail
                name="Test",
                createdAt="2025-08-22T10:00:00Z",
                updatedAt="2025-08-22T12:00:00Z"
            )


class TestN8nClient:
    """Test N8n API client functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock N8n configuration for testing."""
        return N8nConfig(
            api_key="test_api_key_123",
            base_url="http://localhost:5678",
            workflow_id="test_workflow_id"
        )
    
    @pytest.fixture
    def client(self, mock_config):
        """Create N8nClient instance for testing."""
        return N8nClient(mock_config)
    
    def test_client_initialization(self, mock_config):
        """Test client initialization with valid config."""
        client = N8nClient(mock_config)
        
        assert client.config == mock_config
        assert client.base_url == "http://localhost:5678/api/v1"
        assert client.client is None  # Should be initialized on first use
    
    def test_client_initialization_no_api_key(self):
        """Test client initialization fails without API key."""
        config = N8nConfig(api_key="", base_url="http://localhost:5678")
        
        with pytest.raises(ValueError, match="N8n API key is required"):
            N8nClient(config)
    
    def test_normalize_base_url(self, client):
        """Test base URL normalization."""
        # Test various URL formats
        test_cases = [
            ("http://localhost:5678", "http://localhost:5678/api/v1"),
            ("http://localhost:5678/", "http://localhost:5678/api/v1"),
            ("https://n8n.example.com", "https://n8n.example.com/api/v1"),
            ("http://localhost:5678/api/v1", "http://localhost:5678/api/v1"),
            ("https://n8n.example.com/api/v1/", "https://n8n.example.com/api/v1")
        ]
        
        for input_url, expected_url in test_cases:
            result = client._normalize_base_url(input_url)
            assert result == expected_url, f"Failed for input: {input_url}"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality."""
        async with client as c:
            assert c.client is not None
            assert isinstance(c.client, httpx.AsyncClient)
        
        # Client should be closed after context exit
        assert client.client is None
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_list_workflows_success(self, client):
        """Test successful workflow listing with mocked response."""
        # Mock successful API response
        mock_response = {
            "data": [
                {
                    "active": True,
                    "id": "workflow_1",
                    "name": "Test Workflow 1",
                    "nodes": 3,
                    "connections": 2,
                    "createdAt": "2025-08-22T10:00:00Z",
                    "updatedAt": "2025-08-22T11:00:00Z"
                },
                {
                    "active": False,
                    "id": "workflow_2", 
                    "name": "Test Workflow 2",
                    "nodes": 5,
                    "connections": 4,
                    "createdAt": "2025-08-22T09:00:00Z",
                    "updatedAt": "2025-08-22T10:30:00Z"
                }
            ],
            "nextCursor": None
        }
        
        # Set up mock HTTP response
        respx.get("http://localhost:5678/api/v1/workflows").mock(
            return_value=httpx.Response(200, json=mock_response)