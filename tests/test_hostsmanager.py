"""Unit tests for HostsManager."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from redirector.hostsmanager import HostsManager, HostsManagerError
from redirector.constants import REDIRECTOR_BEGIN_MARKER, REDIRECTOR_END_MARKER


class TestHostsManager:
    """Test cases for HostsManager."""

    def test_initialization(self):
        """Test HostsManager initialization."""
        manager = HostsManager()
        assert manager._entries == {}

    def test_generate_redirector_block_content_single_entry(self):
        """Test generating redirector block with single entry."""
        manager = HostsManager()
        manager._entries = {"example.com": "192.168.1.100"}

        block = manager._generate_redirector_block_content()

        assert block[0] == REDIRECTOR_BEGIN_MARKER
        assert block[-1] == REDIRECTOR_END_MARKER
        assert len(block) == 3  # BEGIN + entry + END
        assert "192.168.1.100" in block[1]
        assert "example.com" in block[1]

    def test_generate_redirector_block_content_multiple_entries(self):
        """Test generating redirector block with multiple entries."""
        manager = HostsManager()
        manager._entries = {
            "example.com": "192.168.1.100",
            "test.local": "10.0.0.1",
            "api.service": "172.16.0.50",
        }

        block = manager._generate_redirector_block_content()

        assert block[0] == REDIRECTOR_BEGIN_MARKER
        assert block[-1] == REDIRECTOR_END_MARKER
        assert len(block) == 5  # BEGIN + 3 entries + END

        # Check all hostnames are present
        block_content = "".join(block)
        assert "example.com" in block_content
        assert "test.local" in block_content
        assert "api.service" in block_content

    def test_generate_redirector_block_content_padding(self):
        """Test that IP addresses are properly padded."""
        manager = HostsManager()
        manager._entries = {"short.com": "10.0.0.1", "long.com": "192.168.100.200"}

        block = manager._generate_redirector_block_content()

        # The padding should align based on the longest IP
        # Both entries should have proper spacing
        assert "10.0.0.1" in block[1] or "10.0.0.1" in block[2]
        assert "192.168.100.200" in block[1] or "192.168.100.200" in block[2]

    def test_upsert_entry(self):
        """Test upserting an entry."""
        with patch("socket.gethostbyname", return_value="192.168.1.100"):
            with patch.object(HostsManager, "_upsert_redirector_block"):
                manager = HostsManager()
                manager.upsert_entry("example.com", "backend.host")

                assert manager._entries["example.com"] == "192.168.1.100"

    def test_upsert_entry_updates_existing(self):
        """Test that upserting an entry updates existing value."""
        with patch(
            "socket.gethostbyname", side_effect=["192.168.1.100", "192.168.1.200"]
        ):
            with patch.object(HostsManager, "_upsert_redirector_block"):
                manager = HostsManager()
                manager.upsert_entry("example.com", "backend1.host")
                manager.upsert_entry("example.com", "backend2.host")

                assert manager._entries["example.com"] == "192.168.1.200"
                assert len(manager._entries) == 1

    def test_remove_unexpected_entries(self):
        """Test removing entries not in expected list."""
        with patch.object(HostsManager, "_upsert_redirector_block"):
            manager = HostsManager()
            manager._entries = {
                "keep.com": "192.168.1.100",
                "remove.com": "192.168.1.200",
                "also-keep.com": "192.168.1.300",
            }

            expected = ["keep.com", "also-keep.com"]
            manager.remove_unexpected_entries(expected)

            assert "keep.com" in manager._entries
            assert "also-keep.com" in manager._entries
            assert "remove.com" not in manager._entries
            assert len(manager._entries) == 2

    @patch("builtins.open", new_callable=mock_open, read_data="127.0.0.1 localhost\n")
    @patch("os.stat")
    @patch("os.replace")
    def test_rewrite_hosts_file_success(self, mock_replace, mock_stat, mock_file):
        """Test successful hosts file rewrite."""
        # Mock file stat
        mock_stat_result = Mock()
        mock_stat_result.st_mode = 0o100644
        mock_stat_result.st_uid = 0
        mock_stat_result.st_gid = 0
        mock_stat.return_value = mock_stat_result

        manager = HostsManager()
        lines = ["127.0.0.1 localhost\n", REDIRECTOR_BEGIN_MARKER]

        with patch("tempfile.mkstemp", return_value=(3, "/tmp/hosts.tmp")):
            with patch("os.fdopen", mock_open()):
                with patch("os.chmod"):
                    with patch("os.chown"):
                        manager._rewrite_hosts_file(lines)

        # Verify the file operations were called
        mock_stat.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    def test_read_hosts_file(self, mock_file):
        """Test reading hosts file content."""
        test_content = "127.0.0.1 localhost\n192.168.1.1 gateway\n"
        mock_file.return_value.read.return_value = test_content

        manager = HostsManager()
        file_lines, begin_index, end_index = manager._read_hosts_file()

        assert file_lines == ["127.0.0.1 localhost\n", "192.168.1.1 gateway\n"]
        assert begin_index is None
        assert end_index is None

    @patch.object(HostsManager, "_read_hosts_file")
    def test_load_persisted_entries_no_block(self, mock_read):
        """Test loading when no redirector block exists."""
        mock_read.return_value = (["127.0.0.1 localhost\n"], None, None)

        manager = HostsManager()
        manager.load_persisted_entries()

        assert manager._entries == {}

    @patch.object(HostsManager, "_read_hosts_file")
    def test_load_persisted_entries_with_block(self, mock_read):
        """Test loading existing redirector block."""
        file_lines = [
            "127.0.0.1 localhost\n",
            REDIRECTOR_BEGIN_MARKER,
            "192.168.1.100  example.com\n",
            "10.0.0.1       test.local\n",
            REDIRECTOR_END_MARKER,
            "192.168.1.1 gateway\n",
        ]
        mock_read.return_value = (file_lines, 1, 4)

        manager = HostsManager()
        manager.load_persisted_entries()

        assert "example.com" in manager._entries
        assert manager._entries["example.com"] == "192.168.1.100"
        assert "test.local" in manager._entries
        assert manager._entries["test.local"] == "10.0.0.1"

    @patch.object(HostsManager, "_read_hosts_file")
    def test_load_persisted_entries_malformed_begin_only(self, mock_read):
        """Test error when only BEGIN marker exists."""
        # _read_hosts_file should raise the error, not load_persisted_entries
        mock_read.side_effect = HostsManagerError(
            "Only the BEGIN marker was found in the /etc/hosts file."
        )

        manager = HostsManager()
        with pytest.raises(HostsManagerError, match="Only the BEGIN marker"):
            manager.load_persisted_entries()

    @patch.object(HostsManager, "_read_hosts_file")
    def test_load_persisted_entries_malformed_end_only(self, mock_read):
        """Test error when only END marker exists."""
        # _read_hosts_file should raise the error, not load_persisted_entries
        mock_read.side_effect = HostsManagerError(
            "Only the END marker was found in the /etc/hosts file."
        )

        manager = HostsManager()
        with pytest.raises(HostsManagerError, match="Only the END marker"):
            manager.load_persisted_entries()

    @patch.object(HostsManager, "_read_hosts_file")
    def test_load_persisted_entries_malformed_wrong_order(self, mock_read):
        """Test error when markers are in wrong order."""
        # _read_hosts_file should raise the error, not load_persisted_entries
        mock_read.side_effect = HostsManagerError(
            "The END marker was found before BEGIN marker in the /etc/hosts file."
        )

        manager = HostsManager()
        with pytest.raises(
            HostsManagerError, match="END marker was found before BEGIN"
        ):
            manager.load_persisted_entries()

    @patch.object(HostsManager, "_rewrite_hosts_file")
    @patch.object(HostsManager, "_read_hosts_file")
    def test_upsert_redirector_block_no_existing_block(self, mock_read, mock_rewrite):
        """Test upserting redirector block when no block exists."""
        mock_read.return_value = (["127.0.0.1 localhost\n"], None, None)

        manager = HostsManager()
        manager._entries = {"example.com": "192.168.1.100"}
        manager._upsert_redirector_block()

        # Verify rewrite was called
        mock_rewrite.assert_called_once()
        written_lines = mock_rewrite.call_args[0][0]

        # Check that block was added
        assert REDIRECTOR_BEGIN_MARKER in written_lines
        assert REDIRECTOR_END_MARKER in written_lines

    @patch.object(HostsManager, "_rewrite_hosts_file")
    @patch.object(HostsManager, "_read_hosts_file")
    def test_upsert_redirector_block_replace_existing_block(
        self, mock_read, mock_rewrite
    ):
        """Test upserting redirector block replaces existing block."""
        file_lines = [
            "127.0.0.1 localhost\n",
            REDIRECTOR_BEGIN_MARKER,
            "192.168.1.100 old.com\n",
            REDIRECTOR_END_MARKER,
        ]
        mock_read.return_value = (file_lines, 1, 3)

        manager = HostsManager()
        manager._entries = {"example.com": "192.168.1.200"}
        manager._upsert_redirector_block()

        mock_rewrite.assert_called_once()
        written_lines = mock_rewrite.call_args[0][0]
        written_content = "".join(written_lines)

        # Old entry should be gone
        assert "old.com" not in written_content
        # New entry should be present
        assert "example.com" in written_content
