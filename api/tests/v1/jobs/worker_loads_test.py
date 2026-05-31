from com.qode.qrew.v1.service.core.jobs.worker import WorkerSettings


def test_domain_jobs_registered() -> None:
    names = {f.name for f in WorkerSettings.functions}
    assert "auth.cleanup_expired_tokens" in names
    assert "audit.verify_chain" in names


def test_cron_schedules_present() -> None:
    cron_names = {c.name for c in WorkerSettings.cron_jobs}
    assert "cron:auth.cleanup_expired_tokens" in cron_names
    assert "cron:audit.verify_chain" in cron_names
