import uuid

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_db_session
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.project import Project
from app.models.service import Service
from app.models.user import User


@pytest_asyncio.fixture
async def override_db_session():
    async def _override_db_session():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db_session
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest_asyncio.fixture
async def authenticated_user():
    async with AsyncSessionLocal() as session:
        user = User(
            google_subject=f"service-test-{uuid.uuid4()}",
            email=f"service-{uuid.uuid4()}@example.com",
            name="Service Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        app.dependency_overrides[get_current_user] = lambda: user

        yield user

        app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def other_user():
    async with AsyncSessionLocal() as session:
        user = User(
            google_subject=f"service-other-{uuid.uuid4()}",
            email=f"service-other-{uuid.uuid4()}@example.com",
            name="Other User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        yield user


@pytest_asyncio.fixture
async def app_client(override_db_session, authenticated_user):
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client

async def create_project(user_id):
    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=user_id,
            name=f"Project-{uuid.uuid4()}",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.mark.asyncio
async def test_create_service(app_client, authenticated_user):
    project = await create_project(authenticated_user.id)

    response = await app_client.post(
        f"/api/projects/{project.id}/services",
        json={
            "name": "Backend API",
            "description": "Main backend service",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["project_id"] == str(project.id)
    assert data["name"] == "Backend API"
    assert data["description"] == "Main backend service"


@pytest.mark.asyncio
async def test_create_service_rejects_other_users_project(
    app_client,
    other_user,
):
    project = await create_project(other_user.id)

    response = await app_client.post(
        f"/api/projects/{project.id}/services",
        json={"name": "Unauthorized Service"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_services_returns_project_services(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                Service(
                    project_id=project.id,
                    name="API",
                ),
                Service(
                    project_id=project.id,
                    name="Worker",
                ),
            ]
        )
        await session.commit()

    response = await app_client.get(
        f"/api/projects/{project.id}/services"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["name"] for item in data} == {"API", "Worker"}


@pytest.mark.asyncio
async def test_list_services_rejects_other_users_project(
    app_client,
    other_user,
):
    project = await create_project(other_user.id)

    response = await app_client.get(
        f"/api/projects/{project.id}/services"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_service_requires_ownership(
    app_client,
    other_user,
):
    project = await create_project(other_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="Private API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.get(
        f"/api/projects/{project.id}/services/{service_id}"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_service_rejects_wrong_project(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)
    other_project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.get(
        f"/api/projects/{other_project.id}/services/{service_id}"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_service(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="Old API",
            description="Old description",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.patch(
        f"/api/projects/{project.id}/services/{service_id}",
        json={
            "name": "New API",
            "description": "New description",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "New API"
    assert data["description"] == "New description"


@pytest.mark.asyncio
async def test_update_service_can_clear_description(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
            description="Description to clear",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.patch(
        f"/api/projects/{project.id}/services/{service_id}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.asyncio
async def test_update_service_rejects_empty_patch(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.patch(
        f"/api/projects/{project.id}/services/{service_id}",
        json={},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_service_rejects_null_name(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.patch(
        f"/api/projects/{project.id}/services/{service_id}",
        json={"name": None},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_service_rejects_empty_name(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.patch(
        f"/api/projects/{project.id}/services/{service_id}",
        json={"name": ""},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_service(
    app_client,
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.delete(
        f"/api/projects/{project.id}/services/{service_id}"
    )

    assert response.status_code == 204

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service).where(Service.id == service_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_service_requires_ownership(
    app_client,
    other_user,
):
    project = await create_project(other_user.id)

    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name="Private API",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        service_id = service.id

    response = await app_client.delete(
        f"/api/projects/{project.id}/services/{service_id}"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_project_cascades_to_services(
    authenticated_user,
):
    project = await create_project(authenticated_user.id)

    async with AsyncSessionLocal() as session:
        services = [
            Service(
                project_id=project.id,
                name="API",
            ),
            Service(
                project_id=project.id,
                name="Worker",
            ),
        ]

        session.add_all(services)
        await session.commit()

        service_ids = [service.id for service in services]

        project = await session.get(Project, project.id)
        await session.delete(project)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service).where(Service.id.in_(service_ids))
        )

        assert result.scalars().all() == []