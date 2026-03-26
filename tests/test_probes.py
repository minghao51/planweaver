import pytest
import os
from src.planweaver.probes import (
    FileProbe,
    ApiProbe,
    ImportProbe,
    EnvVarProbe,
    ServiceProbe,
    run_probe,
    PRECONDITION_TYPE_TO_PROBE,
)


class TestFileProbe:
    """Tests for FileProbe."""

    @pytest.fixture
    def probe(self):
        return FileProbe()

    @pytest.mark.asyncio
    async def test_file_exists(self, probe, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = await probe.check(str(test_file))

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_file_does_not_exist(self, probe, tmp_path):
        result = await probe.check(str(tmp_path / "nonexistent.txt"))

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_directory_exists(self, probe, tmp_path):
        result = await probe.check(str(tmp_path))

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_invalid_path_handled(self, probe):
        result = await probe.check("\x00invalid_path")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self, probe, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = await probe.check(f"  {test_file}  ")

        assert result.success is True
        assert result.result is True


class TestApiProbe:
    """Tests for ApiProbe."""

    @pytest.fixture
    def probe(self):
        return ApiProbe()

    @pytest.mark.asyncio
    async def test_invalid_url_rejected(self, probe):
        result = await probe.check("not-a-url")

        assert result.success is False
        assert "Invalid URL" in result.error

    @pytest.mark.asyncio
    async def test_http_url_makes_request(self, probe):
        result = await probe.check("http://example.com")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_https_reachable_site(self, probe):
        result = await probe.check("https://httpbin.org/status/200")

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_https_unreachable_site(self, probe):
        result = await probe.check("https://192.0.2.1/nonexistent")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_timeout_handled(self, probe):
        result = await probe.check("https://10.255.255.1:12345")

        assert result.success is True
        assert result.result is False


class TestImportProbe:
    """Tests for ImportProbe."""

    @pytest.fixture
    def probe(self):
        return ImportProbe()

    @pytest.mark.asyncio
    async def test_builtin_module_available(self, probe):
        result = await probe.check("os")

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_stdlib_module_available(self, probe):
        result = await probe.check("json")

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_nonexistent_module(self, probe):
        result = await probe.check("nonexistent_module_xyz")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_nonexistent_module_returns_false(self, probe):
        result = await probe.check("nonexistent_module_xyz_123")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self, probe):
        result = await probe.check("  os  ")

        assert result.success is True
        assert result.result is True


class TestEnvVarProbe:
    """Tests for EnvVarProbe."""

    @pytest.fixture
    def probe(self):
        return EnvVarProbe()

    @pytest.mark.asyncio
    async def test_env_var_set(self, probe):
        os.environ["TEST_VAR_12345"] = "value"

        result = await probe.check("TEST_VAR_12345")

        assert result.success is True
        assert result.result is True

        del os.environ["TEST_VAR_12345"]

    @pytest.mark.asyncio
    async def test_env_var_not_set(self, probe):
        var_name = "NONEXISTENT_VAR_98765"
        if var_name in os.environ:
            del os.environ[var_name]

        result = await probe.check(var_name)

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_empty_env_var_still_set(self, probe):
        var_name = "EMPTY_VAR_TEST"
        os.environ[var_name] = ""

        result = await probe.check(var_name)

        assert result.success is True
        assert result.result is True

        del os.environ[var_name]

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self, probe):
        os.environ["WS_TEST"] = "value"

        result = await probe.check("  WS_TEST  ")

        assert result.success is True
        assert result.result is True

        del os.environ["WS_TEST"]


class TestServiceProbe:
    """Tests for ServiceProbe."""

    @pytest.fixture
    def probe(self):
        return ServiceProbe()

    @pytest.mark.asyncio
    async def test_localhost_port_refused(self, probe):
        result = await probe.check("localhost:9999")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_invalid_format_no_port(self, probe):
        result = await probe.check("localhost")

        assert result.success is False
        assert "Invalid service expression" in result.error

    @pytest.mark.asyncio
    async def test_invalid_port_non_numeric(self, probe):
        result = await probe.check("localhost:abc")

        assert result.success is False
        assert "Invalid port" in result.error

    @pytest.mark.asyncio
    async def test_invalid_format_too_many_parts(self, probe):
        result = await probe.check("host:port:extra")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self, probe, tmp_path):
        result = await probe.check("  localhost:9999  ")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_service_open_valid_format(self, probe):
        result = await probe.check("localhost:80")

        assert result.success is True


class TestRunProbeFunction:
    """Tests for the run_probe factory function."""

    @pytest.mark.asyncio
    async def test_runs_file_probe(self):
        result = await run_probe("file_exists", "/nonexistent")

        assert result.success is True
        assert result.result is False

    @pytest.mark.asyncio
    async def test_runs_api_probe(self):
        result = await run_probe("api_reachable", "https://httpbin.org/status/200")

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_runs_import_probe(self):
        result = await run_probe("import_available", "os")

        assert result.success is True
        assert result.result is True

    @pytest.mark.asyncio
    async def test_runs_env_var_probe(self):
        os.environ["RUN_PROBE_TEST"] = "1"
        result = await run_probe("env_var_set", "RUN_PROBE_TEST")

        assert result.success is True
        assert result.result is True

        del os.environ["RUN_PROBE_TEST"]

    @pytest.mark.asyncio
    async def test_unknown_precondition_type(self):
        result = await run_probe("unknown_type", "expression")

        assert result.success is False
        assert result.result is None
        assert "Unknown precondition type" in result.error


class TestPreconditionTypeMapping:
    """Tests for PRECONDITION_TYPE_TO_PROBE mapping."""

    def test_all_probe_types_mapped(self):
        expected_types = [
            "file_exists",
            "api_reachable",
            "import_available",
            "env_var_set",
            "service_running",
        ]

        for ptype in expected_types:
            assert ptype in PRECONDITION_TYPE_TO_PROBE
            assert PRECONDITION_TYPE_TO_PROBE[ptype] is not None
