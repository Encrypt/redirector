import random


class _BaseStrategy(object):
    def __init__(self, hosts):
        self._hosts = hosts

    def next_host(self):
        """Get the next host according to the strategy.

        :returns: Host
        """

        raise NotImplementedError


class SequentialStrategy(_BaseStrategy):

    def __init__(self, hosts):
        super().__init__(hosts)
        self._next_index = 0

    def next_host(self):
        """Get the next host in a sequential fashion.

        :returns: Host
        """

        # Identify the next host
        next_host = self._hosts[self._next_index]

        # Process the index for the next call
        self._next_index = (self._next_index + 1) % len(self._hosts)

        return next_host


class RandomStrategy(_BaseStrategy):

    def __init__(self, hosts):
        super().__init__(hosts)
        self._next_index = random.randint(0, len(self._hosts) - 1)

    def next_host(self):
        """Get the next host in a random fashion.

        :returns: Host
        """

        # Identify the next host
        next_host = self._hosts[self._next_index]

        # Process the index for the next call
        next_candidate_index = self._next_index
        while next_candidate_index == self._next_index:
            next_candidate_index = random.randint(0, len(self._hosts) - 1)
        self._next_index = next_candidate_index

        return next_host


strategies = {
    "sequential": SequentialStrategy,
    "random": RandomStrategy
}
