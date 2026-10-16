import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.monitoring_config import MonitoringConfig
from app.models.project import Project
from app.models.service import Service
from app.models.user import User

from types import SimpleNamespace

from app.core.queue import QueueClient, create_redis_pool
from app.models.monitor_check import MonitorCheck

from datetime import datetime, timedelta, timezone

from app.models.monitor_check import MonitorCheck

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_user():
    async with AsyncSessionLocal() as session:
        user = User(
            google_subject=f"monitoring-test-{uuid.uuid4()}",
            email=f"monitoring-{uuid.uuid4()}@example.com",
            name="Monitoring Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        app.dependency_overrides[get_current_user] = lambda: user

        yield user

        app.dependency_overrides.pop(get_current_user, None)
        await cleanup_user_data(user.id)


@pytest_asyncio.fixture
async def other_user():
    async with AsyncSessionLocal() as session:
        user = User(
            google_subject=f"monitoring-other-{uuid.uuid4()}",
            email=f"monitoring-other-{uuid.uuid4()}@example.com",
            name="Other Monitoring User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        yield user

        await cleanup_user_data(user.id)


@pytest_asyncio.fixture
async def project(authenticated_user):
    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=authenticated_user.id,
            name=f"Monitoring Project {uuid.uuid4()}",
            description="Monitoring test project",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        return project


@pytest_asyncio.fixture
async def service(project):
    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=project.id,
            name=f"Monitoring Service {uuid.uuid4()}",
            description="Monitoring test service",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        return service


@pytest_asyncio.fixture
async def other_user_project(other_user):
    async with AsyncSessionLocal() as session:
        project = Project(
            owner_id=other_user.id,
            name=f"Other Project {uuid.uuid4()}",
            description="Other user's project",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        return project


@pytest_asyncio.fixture
async def other_user_service(other_user_project):
    async with AsyncSessionLocal() as session:
        service = Service(
            project_id=other_user_project.id,
            name=f"Other Service {uuid.uuid4()}",
            description="Other user's service",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        return service


async def create_monitoring_config(
    client: AsyncClient,
    project_id,
    service_id,
    **overrides,
):
    payload = {
        "url": "https://example.com/health",
        "method": "GET",
        "interval_seconds": 60,
        "timeout_seconds": 10,
        "enabled": True,
    }

    payload.update(overrides)

    return await client.post(
        f"/api/projects/{project_id}/services/{service_id}/monitoring",
        json=payload,
    )


@pytest.mark.asyncio
async def test_create_monitoring_config(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["service_id"] == str(service.id)
    assert data["url"] == "https://example.com/health"
    assert data["method"] == "GET"
    assert data["interval_seconds"] == 60
    assert data["timeout_seconds"] == 10
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_monitoring_config_with_custom_values(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        url="https://api.example.com/status",
        method="post",
        interval_seconds=120,
        timeout_seconds=30,
        enabled=False,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["url"] == "https://api.example.com/status"
    assert data["method"] == "POST"
    assert data["interval_seconds"] == 120
    assert data["timeout_seconds"] == 30
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_get_monitoring_config(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert create_response.status_code == 201

    response = await client.get(
        f"/api/projects/{project.id}/services/{service.id}/monitoring"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["service_id"] == str(service.id)
    assert data["method"] == "GET"


@pytest.mark.asyncio
async def test_get_missing_monitoring_config_returns_404(
    client,
    authenticated_user,
    project,
    service,
):
    response = await client.get(
        f"/api/projects/{project.id}/services/{service.id}/monitoring"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_monitoring_config_returns_409(
    client,
    authenticated_user,
    project,
    service,
):
    first = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert first.status_code == 201

    second = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_for_missing_service_returns_404(
    client,
    authenticated_user,
    project,
):
    response = await create_monitoring_config(
        client,
        project.id,
        uuid.uuid4(),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_other_users_service_returns_404(
    client,
    authenticated_user,
    project,
    other_user_service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        other_user_service.id,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_wrong_project_for_service_returns_404(
    client,
    authenticated_user,
    project,
    service,
    other_user_project,
):
    response = await create_monitoring_config(
        client,
        other_user_project.id,
        service.id,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_url(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "url": "https://example.com/new-health",
        },
    )

    assert response.status_code == 200
    assert response.json()["url"] == "https://example.com/new-health"


@pytest.mark.asyncio
async def test_update_method_normalizes_to_uppercase(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "method": "post",
        },
    )

    assert response.status_code == 200
    assert response.json()["method"] == "POST"


@pytest.mark.asyncio
async def test_update_interval(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "interval_seconds": 300,
        },
    )

    assert response.status_code == 200
    assert response.json()["interval_seconds"] == 300


@pytest.mark.asyncio
async def test_update_timeout(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "timeout_seconds": 30,
        },
    )

    assert response.status_code == 200
    assert response.json()["timeout_seconds"] == 30


@pytest.mark.asyncio
async def test_update_enabled(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "enabled": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_update_multiple_fields(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "url": "https://api.example.com/health",
            "method": "HEAD",
            "interval_seconds": 180,
            "timeout_seconds": 20,
            "enabled": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["url"] == "https://api.example.com/health"
    assert data["method"] == "HEAD"
    assert data["interval_seconds"] == 180
    assert data["timeout_seconds"] == 20
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_empty_patch_returns_400(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_null_method_returns_422(
    client,
    authenticated_user,
    project,
    service,
):
    await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "method": None,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_method_returns_422(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        method="INVALID",
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_interval_returns_422(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        interval_seconds=0,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_timeout_returns_422(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        timeout_seconds=0,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_url_returns_422(
    client,
    authenticated_user,
    project,
    service,
):
    response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        url="not-a-url",
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_missing_monitoring_config_returns_404(
    client,
    authenticated_user,
    project,
    service,
):
    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={
            "enabled": False,
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_monitoring_config(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert create_response.status_code == 201

    response = await client.delete(
        f"/api/projects/{project.id}/services/{service.id}/monitoring"
    )

    assert response.status_code == 204

    get_response = await client.get(
        f"/api/projects/{project.id}/services/{service.id}/monitoring"
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_delete_returns_404(
    client,
    authenticated_user,
    project,
    other_user_service,
):
    response = await client.delete(
        f"/api/projects/{project.id}/services/{other_user_service.id}/monitoring"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_service_deletion_cascades_monitoring_config(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert create_response.status_code == 201

    async with AsyncSessionLocal() as session:
        db_service = await session.get(Service, service.id)

        assert db_service is not None

        await session.delete(db_service)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MonitoringConfig).where(
                MonitoringConfig.service_id == service.id
            )
        )

        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_run_monitoring_check_enqueues_job(
    client,
    authenticated_user,
    project,
    service,
    monkeypatch,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )

    assert create_response.status_code == 201
    config_id = create_response.json()["id"]

    queue = FakeQueue()
    monkeypatch.setattr(
        app.state,
        "queue",
        queue,
        raising=False,
    )

    response = await client.post(
        f"/api/projects/{project.id}/services/{service.id}/monitoring/run"
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "queued",
        "job_id": "test-job-123",
    }

    assert queue.calls == [
        {
            "job_name": "check_monitor",
            "args": (config_id,),
            "kwargs": {},
        }
    ]

class FakeQueue:
    def __init__(self):
        self.calls = []

    async def enqueue(self, job_name, *args, **kwargs):
        self.calls.append(
            {
                "job_name": job_name,
                "args": args,
                "kwargs": kwargs,
            }
        )
        return SimpleNamespace(job_id="test-job-123")

class CapturingQueue:
    def __init__(self, delegate):
        self.delegate = delegate
        self.jobs = []

    async def enqueue(self, *args, **kwargs):
        job = await self.delegate.enqueue(*args, **kwargs)
        self.jobs.append(job)
        return job


@pytest.mark.asyncio
async def test_run_monitoring_check_for_unauthorized_service_returns_404(
    client,
    authenticated_user,
    project,
    other_user_service,
    monkeypatch,
):
    queue = FakeQueue()
    monkeypatch.setattr(
        app.state,
        "queue",
        queue,
        raising=False,
    )

    response = await client.post(
        f"/api/projects/{project.id}/services/"
        f"{other_user_service.id}/monitoring/run"
    )

    assert response.status_code == 404
    assert queue.calls == []


@pytest.mark.asyncio
async def test_manual_monitoring_check_flows_through_worker_and_persists_results(
    client,
    authenticated_user,
    project,
    service,
    monkeypatch,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
        url="http://nginx/health",
        timeout_seconds=5,
    )
    assert create_response.status_code == 201

    config_id = uuid.UUID(create_response.json()["id"])

    monitoring_path = (
        f"/api/projects/{project.id}/services/"
        f"{service.id}/monitoring"
    )

    pool = await create_redis_pool()
    queue = CapturingQueue(QueueClient(pool))

    monkeypatch.setattr(
        app.state,
        "queue",
        queue,
        raising=False,
    )

    try:
        # First execution: NGINX -> API health endpoint -> HTTP 200.
        response = await client.post(f"{monitoring_path}/run")

        assert response.status_code == 202
        assert response.json()["status"] == "queued"

        success_result = await queue.jobs[-1].result(timeout=20)

        assert success_result["status"] == "completed"
        assert success_result["success"] is True

        # Second execution: a nonexistent path should return HTTP 404.
        update_response = await client.patch(
            monitoring_path,
            json={
                "url": "http://nginx/__sentinel_e2e_not_found__",
            },
        )
        assert update_response.status_code == 200

        response = await client.post(f"{monitoring_path}/run")

        assert response.status_code == 202

        failure_result = await queue.jobs[-1].result(timeout=20)

        assert failure_result["status"] == "completed"
        assert failure_result["success"] is False

        # Confirm that both executions were persisted in PostgreSQL.
        async with AsyncSessionLocal() as session:
            query = (
                select(MonitorCheck)
                .where(
                    MonitorCheck.monitoring_config_id == config_id
                )
                .order_by(MonitorCheck.checked_at.asc())
            )

            result = await session.execute(query)
            checks = result.scalars().all()

        assert len(checks) == 2

        assert checks[0].success is True
        assert checks[0].status_code == 200
        assert checks[0].latency_ms >= 0
        assert checks[0].error is None

        assert checks[1].success is False
        assert checks[1].status_code == 404
        assert checks[1].latency_ms >= 0
        assert checks[1].error is None

    finally:
        await pool.aclose()
        await client.delete(monitoring_path)

@pytest.mark.asyncio
async def test_updating_interval_reschedules_next_check(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )
    assert create_response.status_code == 201

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MonitoringConfig).where(
                MonitoringConfig.service_id == service.id
            )
        )
        config = result.scalar_one()
        original_next_check_at = config.next_check_at

    response = await client.patch(
        f"/api/projects/{project.id}/services/{service.id}/monitoring",
        json={"interval_seconds": 120},
    )
    assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MonitoringConfig).where(
                MonitoringConfig.service_id == service.id
            )
        )
        updated = result.scalar_one()

        assert updated.next_check_at > (
            original_next_check_at + timedelta(seconds=100)
        )


async def cleanup_user_data(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).where(Project.owner_id == user_id)
        )
        projects = result.scalars().all()

        for project in projects:
            result = await session.execute(
                select(Service).where(
                    Service.project_id == project.id
                )
            )

            for service in result.scalars().all():
                await session.delete(service)

            await session.flush()
            await session.delete(project)

        user = await session.get(User, user_id)

        if user is not None:
            await session.delete(user)

        await session.commit()


@pytest.mark.asyncio
async def test_get_latest_monitor_check_returns_newest_result(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )
    assert create_response.status_code == 201

    config_id = uuid.UUID(create_response.json()["id"])
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                MonitorCheck(
                    monitoring_config_id=config_id,
                    checked_at=now - timedelta(minutes=2),
                    success=True,
                    status_code=200,
                    latency_ms=20,
                    error=None,
                ),
                MonitorCheck(
                    monitoring_config_id=config_id,
                    checked_at=now - timedelta(minutes=1),
                    success=False,
                    status_code=503,
                    latency_ms=80,
                    error=None,
                ),
            ]
        )
        await session.commit()

    response = await client.get(
        f"/api/projects/{project.id}/services/{service.id}"
        "/monitoring/checks/latest"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["monitoring_config_id"] == str(config_id)
    assert data["checked_at"] == (
        now - timedelta(minutes=1)
    ).isoformat().replace("+00:00", "Z")
    assert data["success"] is False
    assert data["status_code"] == 503
    assert data["latency_ms"] == 80


@pytest.mark.asyncio
async def test_latest_monitor_check_without_results_returns_404(
    client,
    authenticated_user,
    project,
    service,
):
    create_response = await create_monitoring_config(
        client,
        project.id,
        service.id,
    )
    assert create_response.status_code == 201

    response = await client.get(
        f"/api/projects/{project.id}/services/{service.id}"
        "/monitoring/checks/latest"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_latest_monitor_check_for_unauthorized_service_returns_404(
    client,
    authenticated_user,
    project,
    other_user_service,
):
    response = await client.get(
        f"/api/projects/{project.id}/services/"
        f"{other_user_service.id}/monitoring/checks/latest"
    )

    assert response.status_code == 404
