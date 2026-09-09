from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.monitoring import Incident, MonitorEndpoint


def test_concurrent_incident_inserts_leave_one_open_incident(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'incidents.db'}"
    engine = create_engine(database_url, connect_args={"timeout": 10})
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        endpoint = MonitorEndpoint(url="https://race.example.com/health", http_method="GET")
        session.add(endpoint)
        session.commit()
        monitor_id = endpoint.id

    def insert_incident() -> str:
        try:
            with Session(engine) as session:
                session.add(
                    Incident(
                        monitor_id=monitor_id,
                        opened_at=datetime.utcnow(),
                        trigger_reason="concurrent failure",
                        status="open",
                    )
                )
                session.commit()
            return "inserted"
        except (IntegrityError, OperationalError):
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: insert_incident(), range(2)))

    with Session(engine) as session:
        open_incidents = session.scalars(
            select(Incident).where(Incident.monitor_id == monitor_id, Incident.status == "open")
        ).all()

    assert outcomes.count("inserted") == 1
    assert len(open_incidents) == 1
