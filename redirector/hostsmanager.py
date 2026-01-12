from redirector.constants import (
    HOSTS_FILE_PATH,
    REDIRECTOR_BEGIN_MARKER,
    REDIRECTOR_END_MARKER,
)
import logging
import os
import re
import socket
import stat
import tempfile


class HostsManagerError(Exception):
    pass


class HostsManager(object):

    def __init__(self):

        self._entries = {}

    def _generate_redirector_block_content(self):
        """Generate the Redirector block.

        :returns: List of lines for the /etc/hosts file
        """

        # Add a minimum of two spaces after the IP
        padding = max(len(ip) for ip in self._entries.values()) + 2

        # Generate the block
        block = [REDIRECTOR_BEGIN_MARKER]
        for hostname, ip in self._entries.items():
            padded_ip = ip.ljust(padding)
            block.append(f"{padded_ip}{hostname}\n")
        block.append(REDIRECTOR_END_MARKER)

        return block

    def _rewrite_hosts_file(self, lines):
        """Rewrite the content of the /etc/hosts file.

        :lines: List of lines to write to the file
        :returns: Nothing
        :raises: HostsManagerError in case of error
        """

        # Identify the metadata of the original /etc/hosts file
        hosts_stat = os.stat("/etc/hosts")
        mode = stat.S_IMODE(hosts_stat.st_mode)
        uid = hosts_stat.st_uid
        gid = hosts_stat.st_gid

        # Create a temporary file, preferably in the default temporary directory
        if hosts_stat.st_dev == os.stat(tempfile.gettempdir()).st_dev:
            tmp_fd, tmp_path = tempfile.mkstemp(prefix="redirector_tmp_")
        else:
            tmp_fd, tmp_path = tempfile.mkstemp(prefix=".redirector_tmp_", dir="/etc")

        # Write the result to the temporary file
        with os.fdopen(tmp_fd, "w") as f:
            f.write("".join(lines))

        # Apply the same permissions to the temporary file
        os.chmod(tmp_path, mode)
        try:
            os.chown(tmp_path, uid, gid)
        except PermissionError:
            raise HostsManagerError(
                f'Failed to change the owner / group of the temporary hosts file "{tmp_path}".'
            )

        # Replace the /etc/hosts file
        os.replace(tmp_path, "/etc/hosts")

    def _read_hosts_file(self):
        """Read the /etc/hosts file.

        :returns: Tuple (List with the file lines, BEGIN marker index, END marker index)
        :raises: HostsManagerError in case of error
        """

        # Read the hosts file
        with open("/etc/hosts", "r") as f:
            file_content = f.read()
        file_lines = file_content.splitlines(True)

        # Try to find the markers
        begin_index = None
        end_index = None
        for i, line in enumerate(file_lines):
            if line == REDIRECTOR_BEGIN_MARKER:
                begin_index = i
            if line == REDIRECTOR_END_MARKER:
                end_index = i

        # Make sure the redirector block is correct if found
        if begin_index is not None and end_index is None:
            raise HostsManagerError(
                "Only the BEGIN marker was found in the /etc/hosts file."
            )
        if begin_index is None and end_index is not None:
            raise HostsManagerError(
                "Only the END marker was found in the /etc/hosts file."
            )
        if (
            begin_index is not None
            and end_index is not None
            and begin_index > end_index
        ):
            raise HostsManagerError(
                "The END marker was found before BEGIN marker in the /etc/hosts file."
            )

        return (file_lines, begin_index, end_index)

    def _upsert_redirector_block(self):
        """Update or insert the redirector block in the /etc/hosts file.

        :returns: Nothing
        :raises: HostsManagerError in case of error
        """

        # Read the /etc/hosts file
        original_lines, begin_index, end_index = self._read_hosts_file()

        # If no marker was found, add the redirector block at the end of the file
        if begin_index is None and end_index is None:

            final_lines = original_lines.copy()

            # Add a newline to the last line if it wasn't present
            last_line = final_lines[len(final_lines) - 1]
            if not last_line.endswith("\n"):
                final_lines[len(final_lines) - 1] = f"{last_line}\n"

            # Add the redirector block
            final_lines.extend(self._generate_redirector_block_content())

        # Else, the markers are present, replace the redirector block
        else:

            # Copy the content before the BEGIN marker
            final_lines = original_lines[0:begin_index]

            # Replace the redirector block
            final_lines.extend(self._generate_redirector_block_content())

            # Add the content after the END marker
            final_lines.extend(original_lines[end_index + 1 : len(original_lines)])

        # Rewrite the /etc/hosts file
        self._rewrite_hosts_file(final_lines)

    def remove_redirector_block(self):
        """Remove the redirector block from the /etc/hosts file.

        :returns: Nothing
        :raises: HostsManagerError in case of error
        """

        # Read the /etc/hosts file
        original_lines, begin_index, end_index = self._read_hosts_file()

        # If the markers are present
        if begin_index is not None and end_index is not None:
            logging.debug("Clearing redirector block from /etc/hosts")

            # Remove the block from the lines
            final_lines = original_lines[0:begin_index]
            final_lines.extend(original_lines[end_index + 1 : len(original_lines)])

            # Rewrite the /etc/hosts file
            self._rewrite_hosts_file(final_lines)

    def load_persisted_entries(self):
        """Load the entries defined in the redirector block in the /etc/hosts file.

        ;returns: Nothing
        :raises: HostsManagerError in case of error
        """

        # Read the /etc/hosts file
        file_lines, begin_index, end_index = self._read_hosts_file()

        # If the markers are present
        if begin_index is not None and end_index is not None:
            logging.debug(f"Loading {end_index - begin_index - 1} persisted entries from /etc/hosts")

            # Parse each line between the markers
            for line in file_lines[begin_index + 1 : end_index]:
                res = re.search("^([^ ]+) +(.+)\n$", line)

                # Add the extracted hostname and IP to the entries
                if res is not None:
                    ip, hostname = res.groups()
                    self._entries[hostname] = ip
                else:
                    raise HostsManagerError(
                        "Failed to parse the redirector block in the /etc/hosts file."
                    )

    def upsert_entry(self, local_host, backend_host):
        """Update or insert an entry in the /etc/hosts file.

        :local_host: Canonical hostname to set in the /etc/hosts file
        :backend_host: Host to associate to the canonical hostname
        :returns: Nothing
        :raises: HostsManagerError in case of error
        """

        # Convert the host address to an IP address
        backend_ip = socket.gethostbyname(backend_host)

        # Update the /etc/hosts file if the entry didn't exist or changed
        if local_host not in self._entries or self._entries[local_host] != backend_ip:
            logging.debug(f'Updating /etc/hosts entry: {local_host} -> {backend_ip}')
            self._entries[local_host] = backend_ip
            self._upsert_redirector_block()

    def remove_unexpected_entries(self, expected_hostnames):
        """Remove unexpected entries in the /etc/hosts file.

        :expected_hostnames: List of expected canonical hostnames
        :returns: Nothing
        :raises: HostsManagerError in case of error
        """

        unexpected_hostnames = set(self._entries.keys()).difference(
            set(expected_hostnames)
        )

        if len(unexpected_hostnames) > 0:

            # Remove the unexpected entries
            for hostname in unexpected_hostnames:
                del self._entries[hostname]

            # Update the /etc/hosts file
            self._upsert_redirector_block()
