from sara.infra.activation import environment_activation_report, network_crawler_backends_from_environment


def test_activation_report_is_structured():
    report = environment_activation_report()
    assert set(report) >= {"safe_sandbox", "quantum_crawler", "github_token_present", "hf_token_present"}


def test_crawler_factories_are_real_http_backends():
    backends = network_crawler_backends_from_environment()
    assert len(backends) >= 2
    assert all(hasattr(backend, "fetch") for backend in backends)
