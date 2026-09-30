import uuid

import pytest_asyncio

import httpx
import pytest
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_db_session
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.project import Project
from app.models.user import User


@pytest.fixture
def override_db_session():
    async def _override_db_session():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db_session

    yield

    app.dependency_overrides.pop(get_db_session, None)


@pytest_asyncio.fixture
async def authenticated_user():
    user = User(
        id=uuid.uuid4(),
        google_subject=f"test-subject-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Test User",
    )

    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)

    async def _get_current_user():
        return user

    app.dependency_overrides[get_current_user] = _get_current_user

    yield user

    app.dependency_overrides.pop(get_current_user, None)

@pytest_asyncio.fixture
async def other_user():
    user = User(
        id=uuid.uuid4(),
        google_subject=f"other-test-subject-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@example.com",
        name="Other User",
    )

    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)

    yield user

@pytest_asyncio.fixture
async def app_client(override_db_session, authenticated_user):
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_create_project(app_client, authenticated_user):
    response = await app_client.post(
        "/api/projects",
        json={
            "name": "Sentinel",
            "description": "Distributed monitoring platform",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Sentinel"
    assert data["description"] == "Distributed monitoring platform"
    assert data["owner_id"] == str(authenticated_user.id)


@pytest.mark.asyncio
async def test_list_projects_only_returns_owned_projects(
    app_client,
    authenticated_user,
    other_user
):
    async with AsyncSessionLocal() as session:
        owned_project = Project(
            owner_id=authenticated_user.id,
            name="Owned Project",
        )

        other_project = Project(
            owner_id=other_user.id,
            name="Other Project",
        )

        session.add_all([owned_project, other_project])
        await session.commit()

    response = await app_client.get("/api/projects")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Owned Project"


@pytest.mark.asyncio
async def test_get_project_requires_ownership(
    app_client,
    authenticated_user,
    other_user
):
    other_owner_id = other_user.id

    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=other_owner_id,
            name="Private Project",
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        project_id = project.id

    response = await app_client.get(
        f"/api/projects/{project_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_update_project(app_client, authenticated_user):
    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=authenticated_user.id,
            name="Old Name",
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        project_id = project.id

    response = await app_client.patch(
        f"/api/projects/{project_id}",
        json={
            "name": "New Name",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(app_client, authenticated_user):
    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=authenticated_user.id,
            name="Delete Me",
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        project_id = project.id

    response = await app_client.delete(
        f"/api/projects/{project_id}",
    )

    assert response.status_code == 204

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )

        assert result.scalar_one_or_none() is None